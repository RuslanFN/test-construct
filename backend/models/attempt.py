import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class QuestionResult(BaseModel):
    """Результат по одному вопросу."""
    question_id: uuid.UUID
    is_correct: bool
    given_answer: list[str] = Field(default_factory=list)  # id выбранных ответов/пар
    correct_answer: list[str] = Field(default_factory=list)


class Participant(BaseModel):
    """Данные участника, который проходит тест (без аккаунта)."""
    last_name: str
    first_name: str
    middle_name: str | None = None
    certificate_number: str  # номер сертификата, 10 цифр


class Attempt(BaseModel):
    """
    Попытка прохождения теста (коллекция `attempts`).

    Проходящий тест не имеет аккаунта: его данные (ФИО, номер сертификата)
    хранятся в `participant`. `user_id` оставлен для совместимости/аналитики.
    Хранит итоговый результат и разбивку по вопросам.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    test_id: uuid.UUID
    test_title: str

    user_id: uuid.UUID | None = None
    guest_name: str | None = None  # legacy, больше не заполняется
    participant: Participant | None = None

    score: int = 0          # количество правильных
    total: int = 0          # всего вопросов
    percent: float = 0.0    # процент правильных

    results: list[QuestionResult] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
