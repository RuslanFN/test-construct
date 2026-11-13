import uuid
from datetime import datetime

from pydantic import BaseModel


from models.user import ApprovalStatus, Role


class AdminTestItem(BaseModel):
    id: str
    title: str
    status: str
    public_token: str | None = None
    author_id: str | None = None
    author_username: str | None = None
    questions_count: int = 0
    attempts_count: int = 0
    created_at: datetime


class AdminUserItem(BaseModel):
    id: str
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    role: Role
    is_active: bool
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    approved_at: datetime | None = None
    is_service: bool = False
    created_at: datetime


class AdminUserPatch(BaseModel):
    is_active: bool | None = None
    approval_status: ApprovalStatus | None = None
