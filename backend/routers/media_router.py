import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse

from schemas.media import MediaOut
from services.deps import get_current_user
from services.media_service import (
    MAX_SIZE,
    delete_media,
    get_media,
    save_path,
    store_media,
)

router = APIRouter(prefix='/api/media', tags=['media'])


def _media_url(media_id) -> str:
    return f'/api/media/{media_id}'


def _to_out(doc: dict) -> MediaOut:
    return MediaOut(
        id=str(doc['_id']),
        url=_media_url(doc['_id']),
        filename=doc.get('filename', ''),
        content_type=doc.get('content_type', ''),
        size=doc.get('size', 0),
        width=doc.get('width'),
        height=doc.get('height'),
    )


@router.post('', response_model=MediaOut, status_code=201)
async def upload(file: UploadFile = File(...), current=Depends(get_current_user)):
    # Читаем потоком с обрывом на лимите: не держим в памяти больше MAX_SIZE,
    # даже если клиент пришлёт файл в разы больше.
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_SIZE:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f'Файл слишком большой (максимум {MAX_SIZE // (1024 * 1024)} МБ)',
            )
        chunks.append(chunk)
    data = b''.join(chunks)

    doc = await store_media(data, file.filename or '', current['_id'])
    return _to_out(doc)


@router.get('/{media_id}')
async def get_file(media_id: uuid.UUID):
    """
    Отдача файла. Авторизация не требуется: результаты и вопросы видны
    по ссылке, а id — случайный uuid. Тип отдаём из БД, не угадываем.
    """
    doc = await get_media(media_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Файл не найден')
    path = save_path(doc['stored_name'])
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Файл не найден')
    return FileResponse(
        path,
        media_type=doc.get('content_type') or 'application/octet-stream',
        headers={
            'Cache-Control': 'public, max-age=31536000, immutable',
            'X-Content-Type-Options': 'nosniff',
            'Content-Disposition': 'inline',
        },
    )


@router.delete('/{media_id}', status_code=204)
async def remove(media_id: uuid.UUID, current=Depends(get_current_user)):
    is_admin = current.get('role') == 'admin'
    await delete_media(media_id, current['_id'], is_admin=is_admin)
