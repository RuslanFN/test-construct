from pydantic import BaseModel


class MediaOut(BaseModel):
    id: str
    url: str          # готовая ссылка для <img src>
    filename: str = ''
    content_type: str
    size: int
    width: int | None = None
    height: int | None = None
