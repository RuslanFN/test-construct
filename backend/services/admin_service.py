"""Администрирование: все тесты (поиск/управление) и учётные записи методистов."""
import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status

from db import get_db

from models.user import ApprovalStatus, Role
from schemas.admin import AdminTestItem, AdminUserItem
from services.audit import audit
from services.permissions import is_service


async def search_tests(
    q: str | None = None,
    test_status: str | None = None,
    author_id: str | None = None,
) -> list[AdminTestItem]:
    db = get_db()
    query: dict = {}

    if test_status:
        query['status'] = test_status

    if author_id:
        try:
            query['author.user_id'] = uuid.UUID(author_id)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Некорректный author_id')

    if q:
        q = q.strip()
        # строгое совпадение по токену ИЛИ подстрока по названию
        conds: list[dict] = [
            {'public_token': q},
            {'title': {'$regex': re.escape(q), '$options': 'i'}},
        ]
        # если q — похоже на uuid, поищем и по id
        try:
            conds.append({'_id': uuid.UUID(q)})
        except ValueError:
            pass
        query['$or'] = conds

    # Счётчик попыток по тестам.
    # В pymongo.asynchronous aggregate() — корутина: сначала await, затем итерируем.
    attempts_counts: dict = {}
    cursor = await db['attempts'].aggregate([
        {'$group': {'_id': '$test_id', 'count': {'$sum': 1}}},
    ])
    async for doc in cursor:
        attempts_counts[doc['_id']] = doc['count']

    items: list[AdminTestItem] = []
    cursor = db['tests'].find(query).sort('created_at', -1)
    async for doc in cursor:
        author = doc.get('author', {}) or {}
        items.append(AdminTestItem(
            id=str(doc['_id']),
            title=doc.get('title', ''),
            status=doc.get('status', ''),
            public_token=doc.get('public_token'),
            author_id=str(author.get('user_id')) if author.get('user_id') else None,
            author_username=author.get('username'),
            questions_count=len(doc.get('questions', [])),
            attempts_count=attempts_counts.get(doc['_id'], 0),
            created_at=doc.get('created_at'),
        ))
    return items


async def list_users() -> list[AdminUserItem]:
    items: list[AdminUserItem] = []
    async for doc in get_db()['users'].find({}).sort('created_at', -1):
        items.append(AdminUserItem(
            id=str(doc['_id']),
            username=doc.get('username', ''),
            email=doc.get('email', ''),
            first_name=doc.get('first_name') or None,
            last_name=doc.get('last_name') or None,
            middle_name=doc.get('middle_name') or None,
            role=doc.get('role', Role.METODIST.value),
            is_active=doc.get('is_active', True),
            approval_status=doc.get('approval_status', ApprovalStatus.APPROVED.value),
            approved_at=doc.get('approved_at'),
            is_service=bool(doc.get('is_service')),
            created_at=doc['created_at'],
        ))
    return items


async def get_user_or_404(user_id: uuid.UUID) -> dict:
    doc = await get_db()['users'].find_one({'_id': user_id})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Пользователь не найден')
    return doc


async def update_user(
    user_id: uuid.UUID,
    actor: dict,
    is_active: bool | None = None,
    approval_status: ApprovalStatus | None = None,
) -> None:
    doc = await get_user_or_404(user_id)
    if is_service(doc):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Служебную учётную запись изменять нельзя')

    updates: dict = {}
    actions: list[str] = []

    if approval_status is not None:
        updates['approval_status'] = approval_status.value
        if approval_status == ApprovalStatus.APPROVED:
            updates['approved_at'] = datetime.now(timezone.utc)
            updates['is_active'] = True
            actions.append('user.approved')
        elif approval_status == ApprovalStatus.REJECTED:
            updates['is_active'] = False
            actions.append('user.rejected')
        else:
            actions.append('user.pending')

    if is_active is not None:
        updates['is_active'] = is_active
        actions.append('user.unblocked' if is_active else 'user.blocked')

    if not updates:
        return

    await get_db()['users'].update_one({'_id': user_id}, {'$set': updates})
    for action in actions:
        audit(action, actor=actor, target_id=str(user_id), target_username=doc.get('username'))


async def delete_user_by_admin(user_id: uuid.UUID, actor: dict) -> None:
    doc = await get_user_or_404(user_id)
    if is_service(doc):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Служебную учётную запись нельзя удалить')
    db = get_db()
    await db['users'].delete_one({'_id': user_id})
    # обезличиваем попытки удалённого пользователя (если он проходил тесты)
    await db['attempts'].update_many(
        {'user_id': user_id}, {'$set': {'user_id': None}}
    )
    audit(
        'user.deleted',
        actor=actor,
        target_id=str(user_id),
        target_username=doc.get('username'),
    )
