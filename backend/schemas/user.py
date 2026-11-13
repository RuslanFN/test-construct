import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from models.user import Role

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class UserCreate(BaseModel):
    """Регистрация: клиент присылает пароль в открытом виде."""
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    phone: str | None = None
    role: Role = Role.METODIST
    # согласие на обработку ПДн — обязательно
    pd_consent: bool = False

    @field_validator('email', mode='before')
    @classmethod
    def email_messages_ru(cls, v):
        # Проверяем формат почты сами, чтобы сообщение было на русском
        if not isinstance(v, str) or not _EMAIL_RE.fullmatch(v.strip()):
            raise ValueError('Некорректный формат электронной почты')
        return v.strip()

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = (v or '').strip()
        if len(v) < 3:
            raise ValueError('Логин должен содержать минимум 3 символа')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', v):
            raise ValueError('Логин может содержать только латинские буквы, цифры и символы _ . -')
        return v

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        return v

    @field_validator('first_name', 'last_name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = (v or '').strip()
        if not v:
            raise ValueError('Поле обязательно для заполнения')
        return v

    @field_validator('pd_consent')
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError('Необходимо согласие на обработку персональных данных')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    """Ответ клиенту: без hashed_password."""
    id: str
    username: str
    email: EmailStr
    phone: str | None = None
    first_name: str
    last_name: str
    middle_name: str | None = None
    role: Role
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    user: UserPublic
