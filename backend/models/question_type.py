from enum import Enum


class QuestionType(str, Enum):
    """Тип вопроса. Значения совпадают с фронтендом (schemas.ts)."""
    ONE = 'one'       # один правильный ответ
    SOME = 'some'     # несколько правильных ответов
    MATCH = 'match'   # сопоставление
    TEXT = 'text'     # текстовый ответ
