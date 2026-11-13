import secrets
import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .question import Question


def gen_public_token() -> str:
    return secrets.token_urlsafe(16)


class TestStatus(str, Enum):
    DRAFT = 'draft'          # черновик
    PUBLISHED = 'published'  # опубликован


class Author(BaseModel):
    """
    Денормализованная информация о создателе теста.

    Нужна, чтобы отдавать автора в списке тестов без дополнительного
    запроса в коллекцию `users`. Источник правды — коллекция `users`,
    сюда кладём "снимок" на момент сохранения.
    """
    user_id: uuid.UUID
    username: str


class Test(BaseModel):
    """
    Документ теста в MongoDB (коллекция `tests`).

    Вопросы встроены в документ (`questions`) — это паттерн embed,
    т.к. конструктор сохраняет тест целиком и вопросы не переиспользуются
    между тестами.

    `author` привязывает тест к пользователю, который его создал.
    `public_token` — ссылка для прохождения опубликованного теста.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str
    description: str | None = None

    author: Author
    status: TestStatus = TestStatus.DRAFT
    public_token: str = Field(default_factory=gen_public_token)

    questions: list[Question] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
