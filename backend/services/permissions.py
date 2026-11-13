"""Проверки прав доступа по ролям."""
from models.user import Role


def is_admin(user: dict) -> bool:
    return user.get('role') == Role.ADMIN.value


def is_service(user: dict) -> bool:
    return bool(user.get('is_service'))
