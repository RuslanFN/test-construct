from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

import config

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.access_token_expire_minutes)
    payload = {'sub': subject, 'type': 'access', 'exp': expire}
    return jwt.encode(payload, config.secret_key, algorithm=config.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=config.refresh_token_expire_days)
    payload = {'sub': subject, 'type': 'refresh', 'exp': expire}
    return jwt.encode(payload, config.secret_key, algorithm=config.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Возвращает sub access-токена или None, если токен невалиден/не того типа."""
    return _decode_typed(token, 'access')


def decode_refresh_token(token: str) -> str | None:
    """Возвращает sub refresh-токена или None, если токен невалиден/не того типа."""
    return _decode_typed(token, 'refresh')


def _decode_typed(token: str, expected_type: str) -> str | None:
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.jwt_algorithm])
        # Проверяем тип токена, чтобы access нельзя было использовать как refresh и наоборот.
        if payload.get('type') != expected_type:
            return None
        return payload.get('sub')
    except jwt.PyJWTError:
        return None

