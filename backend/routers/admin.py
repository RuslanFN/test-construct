"""API администратора: поиск/управление всеми тестами и учётными записями."""
import uuid

from fastapi import APIRouter, Depends, Query, status

from schemas.admin import AdminTestItem, AdminUserItem, AdminUserPatch
from services.admin_service import (
    delete_user_by_admin,
    list_users,
    search_tests,
    update_user,
)
from services.deps import require_admin

router = APIRouter(prefix='/api/admin', tags=['admin'], dependencies=[Depends(require_admin)])


@router.get('/tests', response_model=list[AdminTestItem])
async def admin_tests(
    q: str | None = Query(None, description='Название (подстрока) или публичный токен (точно)'),
    test_status: str | None = Query(None, alias='status'),
    author_id: str | None = None,
    current=Depends(require_admin),
):
    return await search_tests(q=q, test_status=test_status, author_id=author_id)


@router.get('/users', response_model=list[AdminUserItem])
async def admin_users(current=Depends(require_admin)):
    return await list_users()


@router.patch('/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def admin_update_user(
    user_id: uuid.UUID,
    payload: AdminUserPatch,
    current=Depends(require_admin),
):
    await update_user(
        user_id,
        current,
        is_active=payload.is_active,
        approval_status=payload.approval_status,
    )


@router.delete('/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(user_id: uuid.UUID, current=Depends(require_admin)):
    await delete_user_by_admin(user_id, current)
