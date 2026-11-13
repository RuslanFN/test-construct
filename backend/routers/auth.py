import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

import config
from db import get_db
from schemas.user import UserCreate, UserLogin, UserPublic
from security import create_access_token, create_refresh_token, decode_refresh_token
from services import ratelimit
from services.deps import get_current_user
from services.user_service import authenticate, create_user, delete_user, user_to_public

router = APIRouter(prefix='/api/auth', tags=['auth'])


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
async def register(payload: UserCreate):
    """Регистрация методиста. Учётка ожидает подтверждения админом — вход пока запрещён."""
    await create_user(payload)
    return {
        'status': 'pending',
        'message': 'Заявка на регистрацию отправлена. Дождитесь подтверждения администратором.',
    }


def _client_ip(request: Request) -> str:
    """IP клиента с учётом прокси (nginx прокидывает X-Forwarded-For)."""
    xff = request.headers.get('x-forwarded-for')
    if xff:
        return xff.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'


@router.post('/login', response_model=UserPublic)
async def login(payload: UserLogin, request: Request, response: Response):
    # защита от перебора паролей: ключ = IP + логин
    rl_key = f'{_client_ip(request)}|{payload.username}'
    try:
        ratelimit.check_and_raise(rl_key)
    except ratelimit.TooManyAttempts as e:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(e),
            headers={'Retry-After': str(e.retry_after)},
        )

    try:
        doc = await authenticate(payload.username, payload.password)
    except HTTPException:
        ratelimit.register_failure(rl_key)
        raise

    ratelimit.reset(rl_key)
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
