import io
import logging
import os
import uuid
import warnings
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

# Бомба декомпрессии: лимит по байтам НЕ защищает от картинки 11000x11000
# весом 117 КБ — при распаковке это ~600 МБ памяти. Ограничиваем число пикселей.
# 24 Мп ≈ 6000x4000: с запасом под фото с телефона, но без гигабайтов в RAM.
MAX_PIXELS = 24_000_000

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


def _open_image(data: bytes) -> Image.Image:
    """
    Открывает изображение, превращая всё «нестандартное» в один 400.

    DecompressionBombWarning (выше ~89 Мп) переводим в исключение: Pillow по
    умолчанию только предупреждает и картинку-бомбу бы пропустил.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        try:
            # verify() ловит битые/поддельные файлы, но после него объект
            # непригоден для чтения — поэтому открываем заново.
            Image.open(io.BytesIO(data)).verify()
            return Image.open(io.BytesIO(data))
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Файл не является изображением поддерживаемого формата',
            )


def _detect_image(data: bytes) -> tuple[str, str, int, int]:
    """
    Определяет формат по СОДЕРЖИМОМУ (magic bytes через Pillow), а не по
    расширению или присланному content-type — им доверять нельзя.

    Возвращает (content_type, extension, width, height).
    """
    img = _open_image(data)
    fmt = (img.format or '').upper()

    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            'Недопустимый формат изображения. Разрешены: PNG, JPEG, WEBP',
        )

    # Размеры (и число пикселей) берутся из заголовка, распаковка ещё не шла —
    # поэтому отказываем дешёво, не тратя память.
    if img.width * img.height > MAX_PIXELS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f'Слишком большое разрешение изображения: {img.width}x{img.height} '
            f'(максимум {MAX_PIXELS // 1_000_000} Мп)',
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


async def store_media(
    data: bytes,
    original_name: str,
    user_id: uuid.UUID | None = None,
) -> dict:
    """
    Проверяет и сохраняет изображение. `data` уже прочитан с жёстким лимитом
    размера на уровне роутера, но размер перепроверяем и здесь.

    `user_id` = None — загрузка без аккаунта (например, участником с публичной
    страницы теста). Все проверки безопасности от способа аутентификации не
    зависят: они внутри этой функции.
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
             media.id, content_type, len(data), user_id or 'без аккаунта')
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


async def delete_media(
    media_id: uuid.UUID,
    user_id: uuid.UUID | None,
    is_admin: bool = False,
) -> None:
    doc = await get_media(media_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Файл не найден')
    # Явная проверка user_id: файл без владельца (загрузка без аккаунта)
    # «своим» не становится, иначе владельцем оказался бы любой аноним.
    if not is_admin and (user_id is None or doc.get('uploaded_by') != user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, 'Нет доступа к этому файлу')
    await delete_media_files([media_id])
