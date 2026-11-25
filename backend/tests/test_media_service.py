"""Тесты сервиса медиа: определение формата, сохранение, удаление, права."""
import io
import uuid

import pytest
from fastapi import HTTPException
from PIL import Image

from services import media_service


def _png_bytes(size=(4, 4), color=(255, 0, 0)):
    buf = io.BytesIO()
    Image.new('RGB', size, color).save(buf, format='PNG')
    return buf.getvalue()


def _jpeg_bytes(size=(4, 4)):
    buf = io.BytesIO()
    Image.new('RGB', size, (0, 255, 0)).save(buf, format='JPEG')
    return buf.getvalue()


def _webp_bytes(size=(4, 4)):
    buf = io.BytesIO()
    Image.new('RGB', size, (0, 0, 255)).save(buf, format='WEBP')
    return buf.getvalue()


# ---------- detect ----------

def test_detect_png():
    ct, ext, w, h = media_service._detect_image(_png_bytes(size=(8, 6)))
    assert ct == 'image/png'
    assert ext == '.png'
    assert (w, h) == (8, 6)


def test_detect_jpeg():
    ct, ext, w, h = media_service._detect_image(_jpeg_bytes())
    assert ct == 'image/jpeg'
    assert ext == '.jpg'


def test_detect_webp():
    ct, ext, w, h = media_service._detect_image(_webp_bytes())
    assert ct == 'image/webp'
    assert ext == '.webp'


def test_detect_invalid_raises_400():
    with pytest.raises(HTTPException) as e:
        media_service._detect_image(b'not an image at all')
    assert e.value.status_code == 400


def test_detect_gif_disallowed():
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), (1, 2, 3)).save(buf, format='GIF')
    with pytest.raises(HTTPException) as e:
        media_service._detect_image(buf.getvalue())
    assert e.value.status_code == 400


# ---------- save_path / traversal ----------

def test_safe_name_unique_ext():
    a = media_service._safe_name('.png')
    b = media_service._safe_name('.png')
    assert a != b
    assert a.endswith('.png')


async def test_save_path_traversal_blocked(tmp_path, monkeypatch):
    monkeypatch.setenv('media_dir', str(tmp_path))
    with pytest.raises(HTTPException) as e:
        media_service.save_path('../etc/passwd')
    assert e.value.status_code == 400


async def test_save_path_ok(tmp_path, monkeypatch):
    monkeypatch.setenv('media_dir', str(tmp_path))
    p = media_service.save_path('abc.png')
    assert p.parent == tmp_path.resolve()


# ---------- store_media ----------

async def test_store_media_success(fake_db):
    uid = uuid.uuid4()
    doc = await media_service.store_media(_png_bytes(), 'orig.png', uid)
    assert doc['content_type'] == 'image/png'
    assert doc['uploaded_by'] == uid
    assert doc['size'] > 0
    # метаданные сохранены и файл на диске существует
    assert len(fake_db['media']._docs) == 1
    assert media_service.save_path(doc['stored_name']).exists()


async def test_store_media_empty_file_400(fake_db):
    with pytest.raises(HTTPException) as e:
        await media_service.store_media(b'', 'x.png', uuid.uuid4())
    assert e.value.status_code == 400


async def test_store_media_too_large_413(fake_db, monkeypatch):
    monkeypatch.setattr(media_service, 'MAX_SIZE', 10)
    with pytest.raises(HTTPException) as e:
        await media_service.store_media(_png_bytes(), 'x.png', uuid.uuid4())
    assert e.value.status_code == 413


async def test_store_media_truncates_long_filename(fake_db):
    long_name = 'a' * 300 + '.png'
    doc = await media_service.store_media(_png_bytes(), long_name, uuid.uuid4())
    assert len(doc['filename']) <= 255


# ---------- get_media ----------

async def test_get_media(fake_db):
    doc = await media_service.store_media(_png_bytes(), 'x.png', uuid.uuid4())
    found = await media_service.get_media(doc['_id'])
    assert found['_id'] == doc['_id']
    assert await media_service.get_media(uuid.uuid4()) is None


# ---------- delete_media_files ----------

async def test_delete_media_files_removes_file_and_doc(fake_db):
    doc = await media_service.store_media(_png_bytes(), 'x.png', uuid.uuid4())
    path = media_service.save_path(doc['stored_name'])
    assert path.exists()
    await media_service.delete_media_files([doc['_id']])
    assert not path.exists()
    assert fake_db['media']._docs == []


async def test_delete_media_files_empty_list_noop(fake_db):
    await media_service.delete_media_files([])  # не падает


# ---------- delete_media (права) ----------

async def test_delete_media_owner(fake_db):
    owner = uuid.uuid4()
    doc = await media_service.store_media(_png_bytes(), 'x.png', owner)
    await media_service.delete_media(doc['_id'], owner, is_admin=False)
    assert fake_db['media']._docs == []


async def test_delete_media_non_owner_forbidden(fake_db):
    doc = await media_service.store_media(_png_bytes(), 'x.png', uuid.uuid4())
    with pytest.raises(HTTPException) as e:
        await media_service.delete_media(doc['_id'], uuid.uuid4(), is_admin=False)
    assert e.value.status_code == 403


async def test_delete_media_admin_allowed(fake_db):
    doc = await media_service.store_media(_png_bytes(), 'x.png', uuid.uuid4())
    await media_service.delete_media(doc['_id'], uuid.uuid4(), is_admin=True)
    assert fake_db['media']._docs == []


async def test_delete_media_not_found_404(fake_db):
    with pytest.raises(HTTPException) as e:
        await media_service.delete_media(uuid.uuid4(), uuid.uuid4(), is_admin=True)
    assert e.value.status_code == 404


async def test_delete_media_anonymous_upload_forbidden(fake_db):
    """Файл без владельца (загрузка без аккаунта) «своим» для удаления не станет."""
    doc = await media_service.store_media(_png_bytes(), 'x.png', None)
    with pytest.raises(HTTPException) as e:
        await media_service.delete_media(doc['_id'], None, is_admin=False)
    assert e.value.status_code == 403

