import re
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ParticipantIn(BaseModel):
    """Данные участника, заполняемые перед прохождением (без аккаунта)."""
    last_name: str
    first_name: str
    middle_name: str | None = None
    certificate_number: str

    @field_validator('last_name', 'first_name')
    @classmethod
    def not_empty(cls, v: str) -> str:
        v = (v or '').strip()
        if not v:
            raise ValueError('Поле обязательно для заполнения')
        if len(v) > 30:
            raise ValueError('Значение слишком длинное (максимум 30 символов)')
        return v

    @field_validator('middle_name')
    @classmethod
    def strip_middle(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if len(v) > 30:
            raise ValueError('Значение слишком длинное (максимум 30 символов)')
        return v or None

    @field_validator('certificate_number')
    @classmethod
    def validate_certificate(cls, v: str) -> str:
        v = (v or '').strip()
        if not re.fullmatch(r'\d{10}', v):
            raise ValueError('Номер сертификата должен состоять из 10 цифр')
        return v


class ParticipantOut(BaseModel):
    last_name: str
    first_name: str
    middle_name: str | None = None
    certificate_number: str


class GivenAnswer(BaseModel):
    """Ответ пользователя на один вопрос при прохождении."""
    question_id: str
    # для one/some/text: id выбранных вариантов; для text — текст ответа в selected
    selected: list[str] = Field(default_factory=list)
    # для match: пары (left_index -> right_index)
    matches: list[tuple[int, int]] = Field(default_factory=list)


class AttemptSubmit(BaseModel):
    participant: ParticipantIn
    answers: list[GivenAnswer] = Field(default_factory=list)


class QuestionResultOut(BaseModel):
    question_id: str
    is_correct: bool
    given_answer: list[str]
    correct_answer: list[str]


class AttemptResult(BaseModel):
    id: str
    test_id: str
    test_title: str
    score: int
    total: int
    percent: float
    results: list[QuestionResultOut]
    created_at: datetime


class AttemptSummary(BaseModel):
    """Краткая попытка для списка результатов у владельца теста."""
    id: str
    test_id: str
    user_id: str | None = None
    guest_name: str | None = None
    participant: ParticipantOut | None = None
    score: int
    total: int
    percent: float
    created_at: datetime


class TestAttemptsOut(BaseModel):
    """Все попытки по тесту + сводка."""
    test_id: str
    test_title: str
    attempts: list[AttemptSummary]
    attempts_count: int
    average_percent: float


class QuestionDetail(BaseModel):
    """Разбор одного вопроса в попытке (человекочитаемо)."""
    question_id: str
    type: str
    text: str
    is_correct: bool
    given: list[str] = Field(default_factory=list)     # что ответил (текстом)
    correct: list[str] = Field(default_factory=list)   # правильный ответ (текстом)


class AttemptDetail(BaseModel):
    """Детальный просмотр одной попытки для владельца теста."""
    id: str
    test_id: str
    test_title: str
    guest_name: str | None = None
    participant: ParticipantOut | None = None
    user_id: str | None = None
    score: int
    total: int
    percent: float
    created_at: datetime
    questions: list[QuestionDetail] = Field(default_factory=list)

