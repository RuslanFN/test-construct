"""Зависимости FastAPI: текущий пользователь по JWT из HttpOnly-куки (или Bearer)."""
import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import config
from db import get_db
from security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    # Приоритет — HttpOnly-куки; Bearer оставлен для совместимости (API-клиенты, тесты).
    token = request.cookies.get(config.cookie_name)
    if token:
        return token
    if credentials is not None:
        return credentials.credentials
    return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Не авторизован')

    sub = decode_access_token(token)
    if sub is None:
        
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Некорректный токен')

    user = await get_db()['users'].find_one({'_id': _as_uuid(sub)})
    if user is None or not user.get('is_active', True):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Пользователь не найден')
    return user


def _as_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Некорректный токен')


async def require_admin(current: dict = Depends(get_current_user)) -> dict:
    """Доступ только администратору."""
    from models.user import Role
    if current.get('role') != Role.ADMIN.value:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Требуются права администратора')
    return current
