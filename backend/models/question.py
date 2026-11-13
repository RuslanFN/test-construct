import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .question_type import QuestionType


class Answer(BaseModel):
    """Вариант ответа. Хранится внутри документа вопроса в MongoDB."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    text: str
    is_correct: bool = False


class MatchPair(BaseModel):
    """Пара для вопроса на сопоставление."""
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    left: str
    right: str


class Question(BaseModel):
    """
    Вопрос. Встраивается в документ теста (коллекция `tests`).

    Поле `type` определяет, какое из полей-ответов используется:
      - ONE / SOME / TEXT -> `answers`
      - MATCH             -> `pairs`
    Поле `text` может быть пустым для типа MATCH (там основной контент в `pairs`).
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    type: QuestionType
    text: str = ""
    required: bool = False

    answers: list[Answer] = Field(default_factory=list)
    pairs: list[MatchPair] = Field(default_factory=list)

    order: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

