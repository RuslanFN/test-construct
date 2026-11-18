import io
import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from PIL import Image, UnidentifiedImageError

from db import get_db
from models.media import MediaFile

log = logging.getLogger(__name__)

# ---- ограничения -----------------------------------------------------------
# Файлы до 5 МБ: в БД и в проекте всего 5 ГБ, поэтому лимит жёсткий.
MAX_SIZE = 5 * 1024 * 1024
CHUNK = 64 * 1024

# Разрешённые форматы. SVG сознательно НЕ разрешён: его можно отрисовать
# как скрипт (XSS), а magic-bytes для SVG ненадёжны.
ALLOWED_FORMATS = {
    'PNG': ('image/png', '.png'),
    'JPEG': ('image/jpeg', '.jpg'),
    'WEBP': ('image/webp', '.webp'),
}


def media_dir() -> Path:
    """Каталог для файлов. По умолчанию /data/uploads (смонтирован на Amvera)."""
    raw = os.getenv('media_dir') or os.getenv('MEDIA_DIR') or '/data/uploads'
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _detect_image(data: bytes) -> tuple[str, str, int, int]:
    """
    Определяет формат по СОДЕРЖИМОМУ (magic bytes через Pillow), а не по
    расширению или присланному content-type — им доверять нельзя.

    Возвращает (content_type, extension, width, height).
    """
    try:
        # verify() ловит битые/поддельные файлы, но после него объект
        # непригоден для чтения — поэтому открываем заново.
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or '').upper()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Файл не является изображением поддерживаемого формата',
        )

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Недопустимый формат изображения. Разрешены: PNG, JPEG, WEBP',
        )

    content_type, ext = ALLOWED_FORMATS[fmt]
    return content_type, ext, img.width, img.height


def _safe_name(ext: str) -> str:
    """Имя файла на диске генерируем сами — оригинальному не доверяем."""
    return f'{uuid.uuid4().hex}{ext}'


def save_path(stored_name: str) -> Path:
    """Путь к файлу с защитой от выхода за пределы каталога (path traversal)."""
    base = media_dir().resolve()
    target = (base / stored_name).resolve()
    if base not in target.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Некорректное имя файла')
    return target


async def store_media(data: bytes, original_name: str, user_id: uuid.UUID) -> dict:
    """
    Проверяет и сохраняет изображение. `data` уже прочитан с жёстким лимитом
    размера на уровне роутера, но размер перепроверяем и здесь.
    """
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, 'Пустой файл')
    if len(data) > MAX_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f'Файл слишком большой: {len(data) // 1024} КБ (максимум {MAX_SIZE // (1024 * 1024)} МБ)',
        )

    content_type, ext, width, height = _detect_image(data)
    stored_name = _safe_name(ext)

    target = save_path(stored_name)
    target.write_bytes(data)

    media = MediaFile(
        filename=(original_name or '')[:255],
        stored_name=stored_name,
        content_type=content_type,
        size=len(data),
        width=width,
        height=height,
        uploaded_by=user_id,
    )
    doc = media.model_dump()
    doc['_id'] = doc.pop('id')
    await get_db()['media'].insert_one(doc)
    log.info('Загружено медиа %s (%s, %d байт) пользователем %s',
             media.id, content_type, len(data), user_id)
    return doc


async def get_media(media_id: uuid.UUID) -> dict | None:
    return await get_db()['media'].find_one({'_id': media_id})


async def delete_media_files(media_ids: list[uuid.UUID]) -> None:
    """
    Удаляет файлы с диска и их метаданные. Вызывается при удалении вопроса,
    чтобы не копить мусор (объём хранилища ограничен).
    Ошибки не пробрасываем: удаление файла не должно ломать сохранение теста.
    """
    ids = [i for i in media_ids if i is not None]
    if not ids:
        return
    db = get_db()
    async for doc in db['media'].find({'_id': {'$in': ids}}):
        stored = doc.get('stored_name')
        if not stored:
            continue
        try:
            save_path(stored).unlink(missing_ok=True)
        except Exception as err:  # noqa: BLE001 — файл мог уже исчезнуть
            log.warning('Не удалось удалить файл медиа %s: %s', stored, err)
    await db['media'].delete_many({'_id': {'$in': ids}})


async def delete_media(media_id: uuid.UUID, user_id: uuid.UUID, is_admin: bool = False) -> None:
    doc = await get_media(media_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Файл не найден')
    if not is_admin and doc.get('uploaded_by') != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Нет доступа к этому файлу')
    await delete_media_files([media_id])
