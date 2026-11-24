import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, EmailStr, Field, field_validator

from models.user import Role

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# Ответ капчи приходит и числом (поле type="number"), и строкой — приводим к строке
# ДО валидации типа, иначе Pydantic отвергает int для поля str (422).
_CaptchaAnswer = Annotated[str | None, BeforeValidator(lambda v: None if v is None else str(v))]


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
    # проверка «я не робот»: токен задачи и ответ (проверяется в роутере)
    captcha_token: str | None = None

    # ответ цифрами: поле type="number" присылает число — принимаем оба типа
    captcha_answer: _CaptchaAnswer = None
    # скрытое поле-ловушка (honeypot): человек его не видит, бот заполняет
    captcha_honeypot: str | None = None

    @field_validator('email', mode='before')
    @classmethod
    def email_messages_ru(cls, v):
        # Проверяем формат почты сами, чтобы сообщение было на русском
        if not isinstance(v, str) or not _EMAIL_RE.fullmatch(v.strip()):
            raise ValueError('Некорректный формат электронной почты')
        v = v.strip()
        if len(v) > 50:
            raise ValueError('Электронная почта слишком длинная (максимум 50 символов)')
        return v

    @field_validator('username')
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = (v or '').strip()
        if len(v) < 3:
            raise ValueError('Логин должен содержать минимум 3 символа')
        if len(v) > 30:
            raise ValueError('Логин слишком длинный (максимум 30 символов)')
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
        if len(v) > 30:
            raise ValueError('Значение слишком длинное (максимум 30 символов)')
        return v

    @field_validator('middle_name')
    @classmethod
    def middle_name_len(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 30:
            raise ValueError('Значение слишком длинное (максимум 30 символов)')
        return v or None

    @field_validator('pd_consent')
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError('Необходимо согласие на обработку персональных данных')
        return v

class UserLogin(BaseModel):
    username: str
    password: str
    # капча требуется сервером (например, после неудачных входов) — необязательна в схеме
    captcha_token: str | None = None
    captcha_answer: _CaptchaAnswer = None
    # скрытое поле-ловушка (honeypot) для отсева ботов
    captcha_honeypot: str | None = None


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
