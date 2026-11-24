import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

import config
from db import get_db
from schemas.captcha import CaptchaOut
from schemas.user import UserCreate, UserLogin, UserPublic
from security import create_access_token, create_refresh_token, decode_refresh_token
from services import captcha, ratelimit
from services.deps import get_current_user
from services.http_client import client_ip
from services.user_service import authenticate, create_user, delete_user, user_to_public

router = APIRouter(prefix='/api/auth', tags=['auth'])

# Лимиты на чувствительные операции (см. services/ratelimit.py)
REGISTER_WINDOW = 600      # окно антиспама регистрации, сек
REGISTER_LIMIT = 3         # заявок за окно с одного IP / на один логин
LOGIN_WINDOW = 300         # окно подсчёта неудачных входов, сек
LOGIN_LIMIT = 5            # неудачных попыток до блокировки
# С какой неудачи требовать капчу на вход: после 2 неудач (т.е. с 3-го запроса)
CAPTCHA_LOGIN_AFTER_FAILS = 2
# Лимит на выдачу капчи (анти-спам запросами задач)
CAPTCHA_WINDOW = 600
CAPTCHA_LIMIT = 60


def _too_many(exc: ratelimit.TooManyAttempts) -> HTTPException:
    """Единый ответ 429 с заголовком Retry-After."""
    return HTTPException(
        status.HTTP_429_TOO_MANY_REQUESTS,
        str(exc),
        headers={'Retry-After': str(exc.retry_after)},
    )


def _captcha_required(detail: str = 'captcha_required') -> HTTPException:
    """400/401 с машиночитаемым кодом: клиент покажет блок капчи и перезапросит задачу."""
    return HTTPException(
        status.HTTP_400_BAD_REQUEST,
        detail={'code': detail, 'message': 'Подтвердите, что вы не робот: решите пример.'},
    )


@router.get('/captcha', response_model=CaptchaOut)
async def get_captcha(request: Request):
    """Выдаёт задачу «я не робот». Под общим IP-лимитом, чтобы не спамили выдачей."""
    keys = ratelimit.keys_captcha(client_ip(request))
    try:
        ratelimit.check(*keys)
    except ratelimit.TooManyAttempts as e:
        raise _too_many(e)
    ratelimit.hit(*keys, window=CAPTCHA_WINDOW, limit=CAPTCHA_LIMIT)

    data = captcha.issue()
    data['expires_in'] = captcha.TTL_SECONDS
    return data


def _set_cookie(response: Response, key: str, value: str, max_age: int) -> None:
    """Кладём JWT в HttpOnly-куку: JS её не прочитает (защита от XSS-кражи)."""
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        path='/',
    )


def _clear_cookie(response: Response, key: str) -> None:
    response.delete_cookie(
        key=key,
        path='/',
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
    )


def _issue_tokens(response: Response, user_id: str) -> None:
    """Ставим access- и refresh-куки для пользователя."""
    _set_cookie(
        response, config.cookie_name,
        create_access_token(user_id), config.cookie_max_age,
    )
    _set_cookie(
        response, config.refresh_cookie_name,
        create_refresh_token(user_id), config.refresh_cookie_max_age,
    )


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, request: Request):
    """Регистрация методиста. Учётка ожидает подтверждения админом — вход пока запрещён."""
    # Антиспам заявок: ограничиваем по IP (чтобы не флудили разными логинами)
    # и по логину (чтобы не заваливали заявками один и тот же).
    keys = ratelimit.keys_register(client_ip(request), payload.username)
    try:
        ratelimit.check(*keys)
    except ratelimit.TooManyAttempts as e:
        raise _too_many(e)

    # Капча на регистрацию — всегда.
    if not captcha.verify(payload.captcha_token, payload.captcha_answer, payload.captcha_honeypot):
        raise _captcha_required()

    await create_user(payload)
    # Учитываем удачную заявку — неудачные (409 валидация) не наказываем,
    # иначе честный пользователь блокируется из-за опечаток.
    ratelimit.hit(*keys, window=REGISTER_WINDOW, limit=REGISTER_LIMIT)
    return {
        'status': 'pending',
        'message': 'Заявка на регистрацию отправлена. Дождитесь подтверждения администратором.',
    }


@router.post('/login', response_model=UserPublic)
async def login(payload: UserLogin, request: Request, response: Response):
    # Защита от перебора: лимит независимо по IP и по логину,
    # иначе сменой второй части ключа можно обойти ограничение.
    keys = ratelimit.keys_login(client_ip(request), payload.username)
    try:
        ratelimit.check(*keys)
    except ratelimit.TooManyAttempts as e:
        raise _too_many(e)

    # Капча на вход — начиная с 3-го запроса (после 2 неудач).
    if ratelimit.count(*keys, window=LOGIN_WINDOW) >= CAPTCHA_LOGIN_AFTER_FAILS:
        if not captcha.verify(payload.captcha_token, payload.captcha_answer, payload.captcha_honeypot):
            raise _captcha_required()

    try:
        doc = await authenticate(payload.username, payload.password)
    except HTTPException:
        ratelimit.hit(*keys, window=LOGIN_WINDOW, limit=LOGIN_LIMIT)
        raise

    ratelimit.reset(*keys)
    _issue_tokens(response, str(doc['_id']))
    return user_to_public(doc)


@router.post('/refresh', response_model=UserPublic)
async def refresh(request: Request, response: Response):
    """Выдаёт новую пару access+refresh по валидному refresh-токену из куки."""
    token = request.cookies.get(config.refresh_cookie_name)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Сессия истекла, войдите заново')

    sub = decode_refresh_token(token)
    if sub is None:
        _clear_cookie(response, config.cookie_name)
        _clear_cookie(response, config.refresh_cookie_name)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Сессия истекла, войдите заново')

    # Пользователь мог быть заблокирован/удалён — проверяем актуальность
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Некорректный токен')
    doc = await get_db()['users'].find_one({'_id': user_id})
    if doc is None or not doc.get('is_active', True):
        _clear_cookie(response, config.cookie_name)
        _clear_cookie(response, config.refresh_cookie_name)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Учётная запись недоступна')

    # Ротация: выдаём обновлённую пару токенов
    _issue_tokens(response, sub)
    return user_to_public(doc)


@router.post('/logout', status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    _clear_cookie(response, config.cookie_name)
    _clear_cookie(response, config.refresh_cookie_name)


@router.get('/me', response_model=UserPublic)
async def me(current=Depends(get_current_user)):
    return user_to_public(current)


@router.delete('/me', status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(response: Response, current=Depends(get_current_user)):
    """Удаление аккаунта и связанных ПДн (право на удаление)."""
    await delete_user(current['_id'])
    _clear_cookie(response, config.cookie_name)
    _clear_cookie(response, config.refresh_cookie_name)
