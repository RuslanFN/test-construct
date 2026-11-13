"""Сид данных: администратор, создаётся при запуске, если его ещё нет."""
import logging
from datetime import datetime, timezone
from typing import Any

import config
from db import get_db
from models.user import Role, User
from security import hash_password, verify_password

logger = logging.getLogger(__name__)


async def ensure_admin() -> None:
    users = get_db()['users']
    existing = await users.find_one({'username': config.admin_username})
    if existing is not None:
        updates: dict[str, Any] = {}
        # гарантируем роль админа
        if existing.get('role') != Role.ADMIN.value:
            updates['role'] = Role.ADMIN.value
        # синхронизируем пароль с .env (чтобы смена admin_password в .env применялась)
        if not verify_password(config.admin_password, existing.get('hashed_password', '')):
            updates['hashed_password'] = hash_password(config.admin_password)
            updates['updated_at'] = datetime.now(timezone.utc)
        # помечаем служебной учётной записью
        if not existing.get('is_service'):
            updates['is_service'] = True
        if updates:
            await users.update_one({'_id': existing['_id']}, {'$set': updates})
            logger.info('Обновлён администратор: %s', config.admin_username)
        return

    admin = User(
        username=config.admin_username,
        email=config.admin_email,
        first_name='Администратор',
        last_name='',
        role=Role.ADMIN,
        hashed_password=hash_password(config.admin_password),
        is_service=True,
    )
    doc: dict[str, Any] = admin.model_dump()
    doc['_id'] = doc.pop('id')
    doc['role'] = admin.role.value
    doc['created_at'] = datetime.now(timezone.utc)
    doc['updated_at'] = datetime.now(timezone.utc)
    await users.insert_one(doc)
    logger.info('Создан администратор: %s', config.admin_username)
