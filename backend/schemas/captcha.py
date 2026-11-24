from pydantic import BaseModel


class CaptchaOut(BaseModel):
    """Задача «я не робот»: пример и подписанный токен."""
    question: str
    token: str
    expires_in: int
