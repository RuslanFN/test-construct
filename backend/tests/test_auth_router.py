"""Интеграционные тесты /api/auth: регистрация, вход, refresh, logout, me, удаление."""
import uuid

import pytest

from services import ratelimit

import config


@pytest.fixture(autouse=True)
def clean_ratelimit():
    ratelimit._fails.clear()
    ratelimit._locked_until.clear()
    yield
    ratelimit._fails.clear()
    ratelimit._locked_until.clear()


def _register_payload(**over):
    data = dict(
        username='newmetodist',
        email='nm@example.com',
        password='password123',
        first_name='Мария',
        last_name='Сидорова',
        pd_consent=True,
    )
    data.update(over)
    return data


# ---------- register ----------

def test_register_success(api_client, fake_db):
    resp = api_client.post('/api/auth/register', json=_register_payload())
    assert resp.status_code == 201
    assert resp.json()['status'] == 'pending'
    # пользователь создан, но неактивен и ждёт подтверждения
    u = next(x for x in fake_db['users']._docs if x['username'] == 'newmetodist')
    assert u['is_active'] is False
    assert u['approval_status'] == 'pending'


def test_register_validation_error_russian(api_client):
    resp = api_client.post('/api/auth/register', json=_register_payload(password='short'))
    assert resp.status_code == 422
    body = resp.json()
    assert 'detail' in body
    assert '8 символов' in body['detail']


def test_register_duplicate_username(api_client, fake_db):
    api_client.post('/api/auth/register', json=_register_payload())
    resp = api_client.post(
        '/api/auth/register',
        json=_register_payload(email='other@example.com'),
    )
    assert resp.status_code == 409


def test_register_without_consent(api_client):
    resp = api_client.post('/api/auth/register', json=_register_payload(pd_consent=False))
    assert resp.status_code == 422


# ---------- login ----------

def test_login_success_sets_cookies(api_client, metodist_doc):
    resp = api_client.post(
        '/api/auth/login',
        json={'username': 'metodist', 'password': 'password123'},
    )
    assert resp.status_code == 200
    assert resp.json()['username'] == 'metodist'
    # куки выставлены
    assert config.cookie_name in resp.cookies or any(
        c.name == config.cookie_name for c in api_client.cookies.jar
    )


def test_login_wrong_password_401(api_client, metodist_doc):
    resp = api_client.post(
        '/api/auth/login',
        json={'username': 'metodist', 'password': 'wrong'},
    )
    assert resp.status_code == 401


def test_login_pending_user_403(api_client, fake_db):
    from tests.conftest import make_user_doc
    fake_db['users']._docs.append(
        make_user_doc(username='pend', approval_status='pending', is_active=False)
    )
    resp = api_client.post('/api/auth/login', json={'username': 'pend', 'password': 'password123'})
    assert resp.status_code == 403


def test_login_triggers_rate_limit_429(api_client, metodist_doc):
    # много неудачных попыток подряд → блокировка
    for _ in range(ratelimit.MAX_FAILS):
        api_client.post('/api/auth/login', json={'username': 'metodist', 'password': 'bad'})
    resp = api_client.post('/api/auth/login', json={'username': 'metodist', 'password': 'bad'})
    assert resp.status_code == 429
    assert 'Retry-After' in resp.headers


# ---------- me ----------

def test_me_requires_auth(api_client):
    resp = api_client.get('/api/auth/me')
    assert resp.status_code == 401


def test_me_with_bearer(api_client, metodist_doc, auth_headers):
    resp = api_client.get('/api/auth/me', headers=auth_headers(metodist_doc))
    assert resp.status_code == 200
    assert resp.json()['username'] == 'metodist'


def test_me_via_cookie(api_client, metodist_doc, auth_headers):
    token = auth_headers(metodist_doc)['Authorization'].split(' ')[1]
    api_client.cookies.set(config.cookie_name, token)
    resp = api_client.get('/api/auth/me')
    assert resp.status_code == 200


def test_me_invalid_token(api_client):
    resp = api_client.get('/api/auth/me', headers={'Authorization': 'Bearer garbage'})
    assert resp.status_code == 401


# ---------- refresh ----------

def test_refresh_without_token_401(api_client):
    resp = api_client.post('/api/auth/refresh')
    assert resp.status_code == 401


def test_refresh_with_valid_token(api_client, metodist_doc):
    from security import create_refresh_token
    api_client.cookies.set(config.refresh_cookie_name, create_refresh_token(str(metodist_doc['_id'])))
    resp = api_client.post('/api/auth/refresh')
    assert resp.status_code == 200
    assert resp.json()['username'] == 'metodist'


def test_refresh_with_access_token_rejected(api_client, metodist_doc):
    from security import create_access_token
    api_client.cookies.set(config.refresh_cookie_name, create_access_token(str(metodist_doc['_id'])))
    resp = api_client.post('/api/auth/refresh')
    assert resp.status_code == 401


def test_refresh_blocked_user_401(api_client, fake_db):
    from tests.conftest import make_user_doc
    from security import create_refresh_token
    user = make_user_doc(username='blk', is_active=False)
    fake_db['users']._docs.append(user)
    api_client.cookies.set(config.refresh_cookie_name, create_refresh_token(str(user['_id'])))
    resp = api_client.post('/api/auth/refresh')
    assert resp.status_code == 401


# ---------- logout ----------

def test_logout_204(api_client):
    resp = api_client.post('/api/auth/logout')
    assert resp.status_code == 204


# ---------- delete me ----------

def test_delete_me(api_client, metodist_doc, auth_headers, fake_db):
    resp = api_client.request(
        'DELETE', '/api/auth/me', headers=auth_headers(metodist_doc)
    )
    assert resp.status_code == 204
    assert not any(u['username'] == 'metodist' for u in fake_db['users']._docs)


def test_delete_me_requires_auth(api_client):
    resp = api_client.request('DELETE', '/api/auth/me')
    assert resp.status_code == 401
