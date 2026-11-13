from datetime import datetime, timezone

import uuid
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class Role(str, Enum):
    ADMIN = 'admin'
    METODIST = 'metodist'


class ApprovalStatus(str, Enum):
    """Статус подтверждения учётной записи администратором."""
    PENDING = 'pending'      # ожидает подтверждения
    APPROVED = 'approved'    # подтверждена
    REJECTED = 'rejected'    # отклонена


class PdConsent(BaseModel):
    """Факт согласия на обработку персональных данных (152-ФЗ)."""
    granted: bool = False
    granted_at: datetime | None = None
    version: str | None = None  # версия текста согласия


class User(BaseModel):
    """
    Документ пользователя, как он хранится в MongoDB (коллекция `users`).

    `id` конвертируется в `_id` при сохранении. Поле `hashed_password`
    живёт только в этой схеме хранения: наружу (в ответах API) оно
    попадать не должно — для этого используется отдельная response-схема.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    username: str
    email: EmailStr
    phone: str | None = None

    first_name: str
    last_name: str
    middle_name: str | None = None

    role: Role = Role.METODIST
    hashed_password: str
    is_active: bool = True
    # служебная учётная запись (главный админ): нельзя удалить/заблокировать,
    # ФИО может быть пустым
    is_service: bool = False

    # подтверждение регистрации администратором
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    approved_at: datetime | None = None

    # согласие на обработку ПДн (обязательное при регистрации)
    pd_consent: PdConsent = Field(default_factory=PdConsent)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


