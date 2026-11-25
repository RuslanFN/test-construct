import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

import config
from db import get_db

from models.user import ApprovalStatus, PdConsent, Role, User
from schemas.user import UserCreate, UserPublic
from security import hash_password, stub_hash, verify_password


def user_to_public(doc: dict) -> UserPublic:
    return UserPublic(
        id=str(doc['_id']),
        username=doc['username'],
        email=doc['email'],
        phone=doc.get('phone'),
        first_name=doc['first_name'],
        last_name=doc['last_name'],
        middle_name=doc.get('middle_name'),
        role=doc['role'],
        is_active=doc.get('is_active', True),
        created_at=doc['created_at'],
    )


async def create_user(payload: UserCreate) -> dict:
    users = get_db()['users']
    if await users.find_one({'username': payload.username}):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Пользователь уже существует')
    if await users.find_one({'email': payload.email}):
        raise HTTPException(status.HTTP_409_CONFLICT, 'Почта уже зарегистрирована')

    user = User(
        username=payload.username,
        email=payload.email,
        phone=payload.phone,
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        # публичная регистрация — всегда методист, роль админа не назначается
        role=Role.METODIST,
        hashed_password=hash_password(payload.password),
        # регистрация требует подтверждения администратором
        is_active=False,
        approval_status=ApprovalStatus.PENDING,
        pd_consent=PdConsent(
            granted=True,
            granted_at=datetime.now(timezone.utc),
            version=config.pd_consent_version,
        ),
    )
    doc: dict[str, Any] = user.model_dump()
    doc['_id'] = doc.pop('id')
    # role сохраняем строкой для удобных запросов
    doc['role'] = user.role.value
    await users.insert_one(doc)
    return doc


async def authenticate(username: str, password: str) -> dict:
    user = await get_db()['users'].find_one({'username': username})
    # bcrypt сверяется ВСЕГДА: если пропускать проверку для несуществующего
    # логина, по времени ответа видно, зарегистрирован ли он (user enumeration).
    hashed = user['hashed_password'] if user else stub_hash()
    password_ok = verify_password(password, hashed)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Неверный логин или пароль')

    approval = user.get('approval_status', ApprovalStatus.APPROVED.value)
    if approval == ApprovalStatus.PENDING.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Учётная запись ожидает подтверждения администратором')
    if approval == ApprovalStatus.REJECTED.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Регистрация отклонена администратором')
    if not user.get('is_active', True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Учётная запись заблокирована')
    return user


async def get_user_by_id(user_id: uuid.UUID) -> dict | None:
    return await get_db()['users'].find_one({'_id': user_id})


async def delete_user(user_id: uuid.UUID) -> None:
    """Удаление аккаунта и связанных ПДн (право субъекта на удаление)."""
    db = get_db()
    res = await db['users'].delete_one({'_id': user_id})
    if res.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Пользователь не найден')
    # обезличиваем/удаляем попытки, привязанные к пользователю
    await db['attempts'].update_many(
        {'user_id': user_id},
        {'$set': {'user_id': None, 'guest_name': None}},
    )

