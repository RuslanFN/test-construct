from fastapi import APIRouter, HTTPException, Request, status

from schemas.attempt import AttemptResult, AttemptSubmit
from schemas.test import TestPublic
from services import ratelimit
from services.attempt_service import submit_attempt
from services.http_client import client_ip
from services.test_service import get_published_by_token, test_to_public

router = APIRouter(prefix='/api/public', tags=['public'])

# Анти-накрутка попыток: один IP не может бесконечно отправлять прохождения
# одного теста (каждая отправка пишет ПДн и раздувает выгрузку Excel).
SUBMIT_WINDOW = 600      # окно, сек
SUBMIT_LIMIT = 30        # отправок за окно на пару IP|тест и суммарно на IP


@router.get('/tests/{token}', response_model=TestPublic)
async def get_public_test(token: str):
    doc = await get_published_by_token(token)
    return test_to_public(doc)


@router.post('/tests/{token}/submit', response_model=AttemptResult)
async def submit(token: str, payload: AttemptSubmit, request: Request):
    doc = await get_published_by_token(token)

    # Участник проходит без аккаунта: ключ — IP + публичный токен теста.
    keys = ratelimit.keys_submit(client_ip(request), token)
    try:
        ratelimit.check(*keys)
    except ratelimit.TooManyAttempts as e:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            str(e),
            headers={'Retry-After': str(e.retry_after)},
        )

    result = await submit_attempt(doc, payload, user_id=None)
    ratelimit.hit(*keys, window=SUBMIT_WINDOW, limit=SUBMIT_LIMIT)
    return result
