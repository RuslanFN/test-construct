from fastapi import APIRouter
from schemas.attempt import AttemptResult, AttemptSubmit
from schemas.test import TestPublic
from services.attempt_service import submit_attempt
from services.test_service import get_published_by_token, test_to_public

router = APIRouter(prefix='/api/public', tags=['public'])


@router.get('/tests/{token}', response_model=TestPublic)
async def get_public_test(token: str):
    doc = await get_published_by_token(token)
    return test_to_public(doc)


@router.post('/tests/{token}/submit', response_model=AttemptResult)
async def submit(token: str, payload: AttemptSubmit):
    doc = await get_published_by_token(token)
    return await submit_attempt(doc, payload, user_id=None)

