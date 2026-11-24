"""Тесты сервиса тестов: создание, редактирование, публикация, права, удаление."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from schemas.test import TestCreate
from services import test_service
from tests.conftest import make_question, make_test_doc


def _payload(**over):
    data = dict(
        title='Мой тест',
        description='Описание',
        status='draft',
        questions=[make_question('one')],
    )
    data.update(over)
    return TestCreate(**data)


# ---------- create_test ----------

async def test_create_test_saves_author_and_audits(fake_db, metodist_doc):
    doc = await test_service.create_test(_payload(), metodist_doc)
    assert doc['title'] == 'Мой тест'
    assert doc['author']['user_id'] == metodist_doc['_id']
    assert doc['status'] == 'draft'
    assert doc['public_token']
    assert fake_db['tests']._docs[0]['title'] == 'Мой тест'


async def test_create_test_published(fake_db, metodist_doc):
    doc = await test_service.create_test(_payload(status='published'), metodist_doc)
    assert doc['status'] == 'published'


# ---------- list_user_tests ----------

async def test_list_user_tests_only_own(fake_db, metodist_doc):
    other = uuid.uuid4()
    fake_db['tests']._docs.append(make_test_doc(author_id=metodist_doc['_id'], title='Мой'))
    fake_db['tests']._docs.append(make_test_doc(author_id=other, title='Чужой'))
    result = await test_service.list_user_tests(metodist_doc)
    assert len(result) == 1
    assert result[0].title == 'Мой'


async def test_list_user_tests_admin_sees_all(fake_db, admin_doc):
    fake_db['tests']._docs.append(make_test_doc(author_id=uuid.uuid4(), title='A'))
    fake_db['tests']._docs.append(make_test_doc(author_id=uuid.uuid4(), title='B'))
    result = await test_service.list_user_tests(admin_doc)
    assert len(result) == 2


async def test_list_user_tests_public_token_hidden_for_draft(fake_db, metodist_doc):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=metodist_doc['_id'], status='draft')
    )
    result = await test_service.list_user_tests(metodist_doc)
    assert result[0].public_token is None


async def test_list_user_tests_public_token_visible_for_published(fake_db, metodist_doc):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=metodist_doc['_id'], status='published', public_token='tokX')
    )
    result = await test_service.list_user_tests(metodist_doc)
    assert result[0].public_token == 'tokX'


# ---------- get_owned_test ----------

async def test_get_owned_test_ok(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'])
    fake_db['tests']._docs.append(t)
    doc = await test_service.get_owned_test(t['_id'], metodist_doc)
    assert doc['_id'] == t['_id']


async def test_get_owned_test_foreign_404(fake_db, metodist_doc):
    t = make_test_doc(author_id=uuid.uuid4())
    fake_db['tests']._docs.append(t)
    with pytest.raises(HTTPException) as e:
        await test_service.get_owned_test(t['_id'], metodist_doc)
    assert e.value.status_code == 404


async def test_get_owned_test_admin_can_access_any(fake_db, admin_doc):
    t = make_test_doc(author_id=uuid.uuid4())
    fake_db['tests']._docs.append(t)
    doc = await test_service.get_owned_test(t['_id'], admin_doc)
    assert doc['_id'] == t['_id']


# ---------- update_test ----------

async def test_update_test_ok(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'], status='draft', title='Старый')
    fake_db['tests']._docs.append(t)
    doc = await test_service.update_test(t['_id'], _payload(title='Новый'), metodist_doc)
    assert doc['title'] == 'Новый'
    assert doc['updated_at'] is not None
    assert fake_db['tests']._docs[0]['title'] == 'Новый'


async def test_update_published_test_conflict(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'], status='published')
    fake_db['tests']._docs.append(t)
    with pytest.raises(HTTPException) as e:
        await test_service.update_test(t['_id'], _payload(), metodist_doc)
    assert e.value.status_code == 409


async def test_update_foreign_test_404(fake_db, metodist_doc):
    t = make_test_doc(author_id=uuid.uuid4())
    fake_db['tests']._docs.append(t)
    with pytest.raises(HTTPException) as e:
        await test_service.update_test(t['_id'], _payload(), metodist_doc)
    assert e.value.status_code == 404


async def test_update_optimistic_lock_conflict(fake_db, metodist_doc):
    now = datetime.now(timezone.utc)
    t = make_test_doc(author_id=metodist_doc['_id'])
    t['updated_at'] = now
    fake_db['tests']._docs.append(t)
    # клиент прислал старую версию (раньше серверной)
    old = now - timedelta(hours=1)
    with pytest.raises(HTTPException) as e:
        await test_service.update_test(t['_id'], _payload(expected_updated_at=old), metodist_doc)
    assert e.value.status_code == 409


async def test_update_optimistic_lock_ok_when_fresh(fake_db, metodist_doc):
    now = datetime.now(timezone.utc)
    t = make_test_doc(author_id=metodist_doc['_id'])
    t['updated_at'] = now
    fake_db['tests']._docs.append(t)
    fresh = now + timedelta(seconds=1)
    doc = await test_service.update_test(
        t['_id'], _payload(expected_updated_at=fresh), metodist_doc
    )
    assert doc['title'] == 'Мой тест'


# ---------- set_status ----------

async def test_set_status_publish(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'], status='draft')
    fake_db['tests']._docs.append(t)
    from models.test import TestStatus
    doc = await test_service.set_status(t['_id'], metodist_doc, TestStatus.PUBLISHED)
    assert doc['status'] == 'published'


async def test_set_status_unpublish(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'], status='published')
    fake_db['tests']._docs.append(t)
    from models.test import TestStatus
    doc = await test_service.set_status(t['_id'], metodist_doc, TestStatus.DRAFT)
    assert doc['status'] == 'draft'


async def test_set_status_foreign_404(fake_db, metodist_doc):
    t = make_test_doc(author_id=uuid.uuid4())
    fake_db['tests']._docs.append(t)
    from models.test import TestStatus
    with pytest.raises(HTTPException) as e:
        await test_service.set_status(t['_id'], metodist_doc, TestStatus.PUBLISHED)
    assert e.value.status_code == 404


# ---------- delete_test ----------

async def test_delete_test_cascades_attempts(fake_db, metodist_doc):
    t = make_test_doc(author_id=metodist_doc['_id'])
    fake_db['tests']._docs.append(t)
    fake_db['attempts']._docs.append({'_id': uuid.uuid4(), 'test_id': t['_id']})
    await test_service.delete_test(t['_id'], metodist_doc)
    assert fake_db['tests']._docs == []
    assert fake_db['attempts']._docs == []


async def test_delete_foreign_test_404(fake_db, metodist_doc):
    t = make_test_doc(author_id=uuid.uuid4())
    fake_db['tests']._docs.append(t)
    with pytest.raises(HTTPException) as e:
        await test_service.delete_test(t['_id'], metodist_doc)
    assert e.value.status_code == 404


# ---------- get_published_by_token / to_public ----------

async def test_get_published_by_token_ok(fake_db):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=uuid.uuid4(), status='published', public_token='abc')
    )
    doc = await test_service.get_published_by_token('abc')
    assert doc['public_token'] == 'abc'


async def test_get_published_by_token_draft_404(fake_db):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=uuid.uuid4(), status='draft', public_token='abc')
    )
    with pytest.raises(HTTPException) as e:
        await test_service.get_published_by_token('abc')
    assert e.value.status_code == 404


def test_to_public_hides_correct_answers():
    q = make_question('one')
    doc = {
        '_id': uuid.uuid4(),
        'title': 'T',
        'description': None,
        'questions': [q],
    }
    public = test_service.test_to_public(doc)
    assert public.title == 'T'
    # в публичном вопросе нет is_correct
    assert public.questions[0].answers[0].text
    assert not hasattr(public.questions[0].answers[0], 'is_correct')


def test_to_public_match_pairs_split():
    q = make_question('match', pairs=[
        {'id': str(uuid.uuid4()), 'left': 'A', 'right': '1'},
        {'id': str(uuid.uuid4()), 'left': 'B', 'right': '2'},
    ])
    doc = {'_id': uuid.uuid4(), 'title': 'T', 'description': None, 'questions': [q]}
    public = test_service.test_to_public(doc)
    assert public.questions[0].pairs_left == ['A', 'B']
    assert public.questions[0].pairs_right == ['1', '2']


def test_to_public_image_urls():
    media_id = uuid.uuid4()
    q = make_question('one', image_ids=[media_id])
    doc = {'_id': uuid.uuid4(), 'title': 'T', 'description': None, 'questions': [q]}
    public = test_service.test_to_public(doc)
    assert public.questions[0].image_urls == [f'/api/media/{media_id}']


def test_test_to_detail():
    t = make_test_doc(author_id=uuid.uuid4(), title='Detail', status='published')
    detail = test_service.test_to_detail(t)
    assert detail.title == 'Detail'
    assert detail.status.value == 'published'
