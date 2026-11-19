"""Тесты зависимостей авторизации: get_current_user, require_admin."""
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import config
from security import create_access_token
from services.deps import get_current_user, require_admin
from tests.conftest import make_user_doc


def _request(cookie_token: str | None = None):
    cookies = {config.cookie_name: cookie_token} if cookie_token else {}
    return SimpleNamespace(cookies=cookies)


async def test_get_current_user_via_bearer(fake_db):
    user = make_user_doc(username='bearer')
    fake_db['users']._docs.append(user)
    token = create_access_token(str(user['_id']))
    creds = SimpleNamespace(credentials=token)
    result = await get_current_user(_request(), creds)
    assert result['username'] == 'bearer'


async def test_get_current_user_via_cookie(fake_db):
    user = make_user_doc(username='cookie')
    fake_db['users']._docs.append(user)
    token = create_access_token(str(user['_id']))
    result = await get_current_user(_request(token), None)
    assert result['username'] == 'cookie'


async def test_get_current_user_no_token_401(fake_db):
    with pytest.raises(HTTPException) as e:
        await get_current_user(_request(), None)
    assert e.value.status_code == 401


async def test_get_current_user_invalid_token_401(fake_db):
    creds = SimpleNamespace(credentials='garbage')
    with pytest.raises(HTTPException) as e:
        await get_current_user(_request(), creds)
    assert e.value.status_code == 401


async def test_get_current_user_not_found_401(fake_db):
    import uuid
    token = create_access_token(str(uuid.uuid4()))
    creds = SimpleNamespace(credentials=token)
    with pytest.raises(HTTPException) as e:
        await get_current_user(_request(), creds)
    assert e.value.status_code == 401


async def test_get_current_user_inactive_401(fake_db):
    user = make_user_doc(username='inactive', is_active=False)
    fake_db['users']._docs.append(user)
    token = create_access_token(str(user['_id']))
    creds = SimpleNamespace(credentials=token)
    with pytest.raises(HTTPException) as e:
        await get_current_user(_request(), creds)
    assert e.value.status_code == 401


async def test_get_current_user_bad_uuid_sub_401(fake_db):
    # токен с sub, не являющимся UUID
    token = create_access_token('not-a-uuid')
    creds = SimpleNamespace(credentials=token)
    with pytest.raises(HTTPException) as e:
        await get_current_user(_request(), creds)
    assert e.value.status_code == 401


async def test_require_admin_ok(admin_doc):
    result = await require_admin(admin_doc)
    assert result is admin_doc


async def test_require_admin_forbidden(metodist_doc):
    with pytest.raises(HTTPException) as e:
        await require_admin(metodist_doc)
    assert e.value.status_code == 403
