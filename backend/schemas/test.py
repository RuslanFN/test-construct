import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from models.question import Question
from models.test import TestStatus


class TestCreate(BaseModel):
    """Что присылает конструктор при сохранении/публикации теста."""
    title: str
    description: str | None = None
    status: TestStatus = TestStatus.DRAFT
    questions: list[Question] = Field(default_factory=list)
    # для защиты от затирания: версия, которую видел клиент при загрузке
    expected_updated_at: datetime | None = None


class TestSummary(BaseModel):
    """Краткая карточка теста для списка в профиле."""
    id: str
    title: str
    status: TestStatus
    public_token: str | None = None  # ссылка, только если опубликован
    questions_count: int


class TestDetail(BaseModel):
    """Тест для конструктора (владелец)."""
    id: str
    title: str
    description: str | None = None
    status: TestStatus
    public_token: str
    questions: list[Question]
    updated_at: datetime


class TestPublic(BaseModel):
    """Тест для прохождения по ссылке: без правильных ответов."""
    id: str
    title: str
    description: str | None = None
    questions: list['QuestionPublic']


class AnswerPublic(BaseModel):
    id: str
    text: str


class QuestionPublic(BaseModel):
    id: str
    type: str
    text: str
    required: bool = False
    answers: list[AnswerPublic] = Field(default_factory=list)
    pairs_left: list[str] = Field(default_factory=list)
    pairs_right: list[str] = Field(default_factory=list)


TestPublic.model_rebuild()


