"""Сжимающаяся «бомба»: маленький файл, огромное разрешение.

Лимит MAX_SIZE считается по байтам, а однотонная PNG 11000x11000 весит
~117 КБ и при распаковке занимает сотни МБ. Pillow выше своего порога
(~89 Мп) выдаёт только предупреждение, поэтому отказ делаем сами.
"""
import io
import uuid

import pytest
from fastapi import HTTPException
from PIL import Image

from services import media_service


def _solid_image(width: int, height: int, fmt: str = 'PNG') -> bytes:
    """Однотонная картинка: сжимается в единицы КБ при любом разрешении."""
    buf = io.BytesIO()
    Image.new('L', (width, height), 0).save(buf, format=fmt)
    return buf.getvalue()


async def test_decompression_bomb_rejected(fake_db):
    data = _solid_image(11000, 11000)
    # бомба обязана проходить лимит по байтам, иначе тест проверяет не то
    assert len(data) < media_service.MAX_SIZE

    with pytest.raises(HTTPException) as e:
        await media_service.store_media(data, 'bomb.png', uuid.uuid4())

    assert e.value.status_code == 400
    # на диск ничего не легло
    assert fake_db['media']._docs == []


async def test_bomb_above_pillow_warning_limit_rejected(fake_db):
    """Выше собственного порога Pillow (~89 Мп) — тоже отказ, а не предупреждение."""
    data = _solid_image(10000, 10000)  # 100 Мп
    with pytest.raises(HTTPException) as e:
        await media_service.store_media(data, 'bomb.png', uuid.uuid4())
    assert e.value.status_code == 400


async def test_max_size_image_accepted(fake_db):
    """Ровно на границе MAX_PIXELS картинка принимается (проверка не строже нужного)."""
    limit = media_service.MAX_PIXELS
    width, height = 6000, limit // 6000  # 24 000 000 пикселей
    assert width * height <= limit

    doc = await media_service.store_media(_solid_image(width, height), 'ok.png', uuid.uuid4())
    assert doc['width'] == width
    assert doc['height'] == height


async def test_upload_without_account_allowed(fake_db):
    """Загрузка без аккаунта (будущая публичная страница) проходит те же проверки."""
    doc = await media_service.store_media(_solid_image(8, 8), 'anon.png', None)
    assert doc['uploaded_by'] is None

    # и бомбу так тоже не пропустит
    with pytest.raises(HTTPException) as e:
        await media_service.store_media(_solid_image(11000, 11000), 'bomb.png', None)
    assert e.value.status_code == 400
