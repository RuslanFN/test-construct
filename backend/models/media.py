import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MediaFile(BaseModel):
    """
    Загруженное изображение (коллекция `media`).

    Сам файл лежит на диске (`MEDIA_DIR`), здесь — только метаданные.
    `stored_name` — сгенерированное безопасное имя (uuid + расширение):
    оригинальное имя из запроса на диск никогда не попадает.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    filename: str = ''            # оригинальное имя (только для отображения)
    stored_name: str              # имя файла на диске, напр. "<uuid>.png"
    content_type: str             # image/png | image/jpeg | image/webp
    size: int                     # байт
    width: int | None = None
    height: int | None = None
    uploaded_by: uuid.UUID        # владелец файла
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
