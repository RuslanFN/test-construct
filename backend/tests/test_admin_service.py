"""Тесты административного сервиса: поиск тестов, управление пользователями."""
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from services import admin_service
from tests.conftest import make_test_doc, make_user_doc


def _put_user(fake_db, **over):
    doc = make_user_doc(**over)
    fake_db['users']._docs.append(doc)
    return doc


def _put_test(fake_db, **over):
    doc = make_test_doc(author_id=over.pop('author_id', uuid.uuid4()), **over)
    fake_db['tests']._docs.append(doc)
    return doc


# ---------- search_tests ----------

async def test_search_all(fake_db):
    _put_test(fake_db, title='A')
    _put_test(fake_db, title='B')
    items = await admin_service.search_tests()
    assert len(items) == 2


async def test_search_by_status(fake_db):
    _put_test(fake_db, title='A', status='draft')
    _put_test(fake_db, title='B', status='published')
    items = await admin_service.search_tests(test_status='published')
    assert len(items) == 1
    assert items[0].title == 'B'


async def test_search_by_title_substring(fake_db):
    _put_test(fake_db, title='Математика')
    _put_test(fake_db, title='Русский')
    items = await admin_service.search_tests(q='матем')
    assert len(items) == 1
    assert items[0].title == 'Математика'


async def test_search_by_exact_token(fake_db):
    _put_test(fake_db, title='A', public_token='tokenA')
    _put_test(fake_db, title='B', public_token='tokenB')
    items = await admin_service.search_tests(q='tokenA')
    assert len(items) == 1
    assert items[0].title == 'A'


async def test_search_by_id(fake_db):
    t = _put_test(fake_db, title='ByID')
    items = await admin_service.search_tests(q=str(t['_id']))
    assert len(items) == 1


async def test_search_by_author(fake_db):
    a = uuid.uuid4()
    _put_test(fake_db, title='A', author_id=a)
    _put_test(fake_db, title='B')
    items = await admin_service.search_tests(author_id=str(a))
    assert len(items) == 1
    assert items[0].title == 'A'


async def test_search_invalid_author_400(fake_db):
    with pytest.raises(HTTPException) as e:
        await admin_service.search_tests(author_id='not-a-uuid')
    assert e.value.status_code == 400


async def test_search_attempts_count(fake_db):
    t = _put_test(fake_db, title='A')
    fake_db['attempts']._docs.append({'_id': uuid.uuid4(), 'test_id': t['_id']})
    fake_db['attempts']._docs.append({'_id': uuid.uuid4(), 'test_id': t['_id']})
    items = await admin_service.search_tests()
    assert items[0].attempts_count == 2


# ---------- list_users ----------

async def test_list_users(fake_db):
    _put_user(fake_db, username='user1')
    _put_user(fake_db, username='user2')
    items = await admin_service.list_users()
    assert len(items) == 2


# ---------- update_user ----------

async def test_update_user_approve(fake_db, admin_doc):
    target = _put_user(fake_db, username='pending1', approval_status='pending', is_active=False)
    from models.user import ApprovalStatus
    await admin_service.update_user(
        target['_id'], admin_doc, approval_status=ApprovalStatus.APPROVED
    )
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['approval_status'] == 'approved'
    assert doc['is_active'] is True
    assert doc['approved_at'] is not None


async def test_update_user_reject(fake_db, admin_doc):
    target = _put_user(fake_db, username='pending2', approval_status='pending')
    from models.user import ApprovalStatus
    await admin_service.update_user(
        target['_id'], admin_doc, approval_status=ApprovalStatus.REJECTED
    )
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['approval_status'] == 'rejected'
    assert doc['is_active'] is False


async def test_update_user_block_unblock(fake_db, admin_doc):
    target = _put_user(fake_db, username='user3', is_active=True)
    await admin_service.update_user(target['_id'], admin_doc, is_active=False)
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['is_active'] is False
    await admin_service.update_user(target['_id'], admin_doc, is_active=True)
    doc = next(u for u in fake_db['users']._docs if u['_id'] == target['_id'])
    assert doc['is_active'] is True


async def test_update_service_account_forbidden(fake_db, admin_doc):
    # admin_doc помечен is_service=True
    with pytest.raises(HTTPException) as e:
        await admin_service.update_user(admin_doc['_id'], admin_doc, is_active=False)
    assert e.value.status_code == 403


async def test_update_unknown_user_404(fake_db, admin_doc):
    with pytest.raises(HTTPException) as e:
        await admin_service.update_user(uuid.uuid4(), admin_doc, is_active=False)
    assert e.value.status_code == 404


async def test_update_user_no_changes_noop(fake_db, admin_doc):
    target = _put_user(fake_db, username='user4')
    # без изменений — просто не падает
    await admin_service.update_user(target['_id'], admin_doc)


# ---------- delete_user_by_admin ----------

async def test_delete_user_by_admin(fake_db, admin_doc):
    target = _put_user(fake_db, username='todelete')
    fake_db['attempts']._docs.append({'_id': uuid.uuid4(), 'user_id': target['_id']})
    await admin_service.delete_user_by_admin(target['_id'], admin_doc)
    assert not any(u['username'] == 'todelete' for u in fake_db['users']._docs)
    assert fake_db['attempts']._docs[0]['user_id'] is None


async def test_delete_service_account_forbidden(fake_db, admin_doc):
    with pytest.raises(HTTPException) as e:
        await admin_service.delete_user_by_admin(admin_doc['_id'], admin_doc)
    assert e.value.status_code == 403


async def test_delete_unknown_user_404(fake_db, admin_doc):
    with pytest.raises(HTTPException) as e:
        await admin_service.delete_user_by_admin(uuid.uuid4(), admin_doc)
    assert e.value.status_code == 404
