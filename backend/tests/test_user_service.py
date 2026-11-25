"""Тесты сервиса пользователей: создание, аутентификация, удаление."""
import uuid

import pytest
from fastapi import HTTPException

from schemas.user import UserCreate
from services import user_service
from tests.conftest import make_user_doc


def _payload(**over):
    data = dict(
        username='newuser',
        email='new@example.com',
        password='password123',
        first_name='Пётр',
        last_name='Петров',
        pd_consent=True,
    )
    data.update(over)
    return UserCreate(**data)


# ---------- create_user ----------

async def test_create_user_success(fake_db):
    doc = await user_service.create_user(_payload())
    assert doc['username'] == 'newuser'
    assert doc['role'] == 'metodist'  # всегда методист
    assert doc['is_active'] is False  # ждёт подтверждения
    assert doc['approval_status'] == 'pending'
    assert doc['pd_consent']['granted'] is True
    assert 'id' not in doc and '_id' in doc
    assert fake_db['users']._docs[0]['username'] == 'newuser'


async def test_create_user_forces_metodist_role(fake_db):
    # даже если в payload указана роль admin — создаётся методист
    payload = _payload()
    payload.role = 'admin'
    doc = await user_service.create_user(payload)
    assert doc['role'] == 'metodist'


async def test_create_user_duplicate_username(fake_db):
    await user_service.create_user(_payload(username='dup', email='a@example.com'))
    with pytest.raises(HTTPException) as e:
        await user_service.create_user(_payload(username='dup', email='b@example.com'))
    assert e.value.status_code == 409


async def test_create_user_duplicate_email(fake_db):
    await user_service.create_user(_payload(username='user1', email='same@example.com'))
    with pytest.raises(HTTPException) as e:
        await user_service.create_user(_payload(username='user2', email='same@example.com'))
    assert e.value.status_code == 409


# ---------- authenticate ----------

async def test_authenticate_success(fake_db):
    fake_db['users']._docs.append(make_user_doc(username='ok', password='secret123'))
    doc = await user_service.authenticate('ok', 'secret123')
    assert doc['username'] == 'ok'


async def test_authenticate_wrong_password(fake_db):
    fake_db['users']._docs.append(make_user_doc(username='ok', password='secret123'))
    with pytest.raises(HTTPException) as e:
        await user_service.authenticate('ok', 'wrong')
    assert e.value.status_code == 401


async def test_authenticate_unknown_user(fake_db):
    with pytest.raises(HTTPException) as e:
        await user_service.authenticate('ghost', 'x')
    assert e.value.status_code == 401


async def test_authenticate_unknown_user_still_verifies(fake_db, monkeypatch):
    """Для несуществующего логина bcrypt всё равно вызывается.

    Иначе по времени ответа видно, зарегистрирован ли логин (user enumeration).
    Проверяем сам факт вызова, а не тайминги: они в тестах нестабильны.
    """
    calls = []

    def fake_verify(plain: str, hashed: str) -> bool:
        calls.append(hashed)
        return False

    monkeypatch.setattr(user_service, 'verify_password', fake_verify)
    with pytest.raises(HTTPException):
        await user_service.authenticate('nobody-here', 'x')

    # проверки — ПОСЛЕ вызова, иначе они выполняются внутри pytest.raises
    assert len(calls) == 1
    assert calls[0]  # передан эталонный хэш, а не пустая строка


async def test_authenticate_pending(fake_db):
    fake_db['users']._docs.append(
        make_user_doc(username='p', approval_status='pending', is_active=False)
    )
    with pytest.raises(HTTPException) as e:
        await user_service.authenticate('p', 'password123')
    assert e.value.status_code == 403
    assert 'подтвержден' in e.value.detail


async def test_authenticate_rejected(fake_db):
    fake_db['users']._docs.append(
        make_user_doc(username='r', approval_status='rejected', is_active=False)
    )
    with pytest.raises(HTTPException) as e:
        await user_service.authenticate('r', 'password123')
    assert e.value.status_code == 403
    assert 'отклонена' in e.value.detail


async def test_authenticate_blocked(fake_db):
    fake_db['users']._docs.append(
        make_user_doc(username='b', approval_status='approved', is_active=False)
    )
    with pytest.raises(HTTPException) as e:
        await user_service.authenticate('b', 'password123')
    assert e.value.status_code == 403
    assert 'заблокирована' in e.value.detail


# ---------- user_to_public ----------

async def test_user_to_public_hides_password(fake_db):
    doc = make_user_doc(username='pub')
    public = user_service.user_to_public(doc)
    assert not hasattr(public, 'hashed_password')
    assert public.username == 'pub'
    assert public.id == str(doc['_id'])


# ---------- delete_user ----------

async def test_delete_user_and_anonymize_attempts(fake_db):
    user = make_user_doc(username='del')
    fake_db['users']._docs.append(user)
    fake_db['attempts']._docs.append({'_id': uuid.uuid4(), 'user_id': user['_id'], 'guest_name': 'x'})

    await user_service.delete_user(user['_id'])
    assert not any(u['username'] == 'del' for u in fake_db['users']._docs)
    att = fake_db['attempts']._docs[0]
    assert att['user_id'] is None
    assert att['guest_name'] is None


async def test_delete_unknown_user_404(fake_db):
    with pytest.raises(HTTPException) as e:
        await user_service.delete_user(uuid.uuid4())
    assert e.value.status_code == 404


async def test_get_user_by_id(fake_db):
    user = make_user_doc(username='g')
    fake_db['users']._docs.append(user)
    found = await user_service.get_user_by_id(user['_id'])
    assert found['username'] == 'g'
    assert await user_service.get_user_by_id(uuid.uuid4()) is None
