"""Интеграционные тесты /api/media: загрузка, получение, удаление, лимиты."""
import io
import uuid

from PIL import Image


def _png_bytes(size=(4, 4)):
    buf = io.BytesIO()
    Image.new('RGB', size, (255, 0, 0)).save(buf, format='PNG')
    return buf.getvalue()


def _upload(api_client, headers, data, filename='img.png', content_type='image/png'):
    return api_client.post(
        '/api/media',
        headers=headers,
        files={'file': (filename, data, content_type)},
    )


def test_upload_requires_auth(api_client):
    resp = api_client.post('/api/media', files={'file': ('a.png', _png_bytes(), 'image/png')})
    assert resp.status_code == 401


def test_upload_success(api_client, metodist_doc, auth_headers, fake_db):
    resp = _upload(api_client, auth_headers(metodist_doc), _png_bytes())
    assert resp.status_code == 201
    body = resp.json()
    assert body['content_type'] == 'image/png'
    assert body['url'] == f"/api/media/{body['id']}"
    assert len(fake_db['media']._docs) == 1


def test_upload_invalid_file_400(api_client, metodist_doc, auth_headers):
    resp = _upload(api_client, auth_headers(metodist_doc), b'not-an-image', 'x.txt', 'text/plain')
    assert resp.status_code == 400


def test_upload_too_large_413(api_client, metodist_doc, auth_headers, monkeypatch):
    import services.media_service as ms
    monkeypatch.setattr(ms, 'MAX_SIZE', 10)
    resp = _upload(api_client, auth_headers(metodist_doc), _png_bytes())
    assert resp.status_code == 413


def test_get_file(api_client, metodist_doc, auth_headers):
    up = _upload(api_client, auth_headers(metodist_doc), _png_bytes()).json()
    resp = api_client.get(f"/api/media/{up['id']}")
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('image/png')
    assert resp.headers['x-content-type-options'] == 'nosniff'


def test_get_unknown_file_404(api_client):
    resp = api_client.get(f'/api/media/{uuid.uuid4()}')
    assert resp.status_code == 404


def test_delete_owner(api_client, metodist_doc, auth_headers, fake_db):
    up = _upload(api_client, auth_headers(metodist_doc), _png_bytes()).json()
    resp = api_client.delete(f"/api/media/{up['id']}", headers=auth_headers(metodist_doc))
    assert resp.status_code == 204
    assert fake_db['media']._docs == []


def test_delete_non_owner_403(api_client, metodist_doc, auth_headers, fake_db):
    from tests.conftest import make_user_doc
    up = _upload(api_client, auth_headers(metodist_doc), _png_bytes()).json()
    other = make_user_doc(username='otheruser')
    fake_db['users']._docs.append(other)
    resp = api_client.delete(f"/api/media/{up['id']}", headers=auth_headers(other))
    assert resp.status_code == 403
