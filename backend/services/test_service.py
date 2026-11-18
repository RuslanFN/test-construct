import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from db import get_db
from models.test import Author, Test, TestStatus
from schemas.test import (
    AnswerPublic,
    QuestionPublic,
    TestCreate,
    TestDetail,
    TestPublic,
    TestSummary,
)
from services.audit import audit
from services.permissions import is_admin


def _ownership_filter(user: dict) -> dict:
    """Админ видит любые тесты, методист — только свои."""
    if is_admin(user):
        return {}
    return {'author.user_id': user['_id']}


async def create_test(payload: TestCreate, author_doc: dict) -> dict:
    test = Test(
        title=payload.title,
        description=payload.description,
        author=Author(user_id=author_doc['_id'], username=author_doc['username']),
        status=payload.status,
        questions=payload.questions,
    )
    doc: dict[str, Any] = test.model_dump()
    doc['_id'] = doc.pop('id')
    # enum'ы в строку для запросов
    doc['status'] = test.status.value
    await get_db()['tests'].insert_one(doc)
    audit('test.created', actor=author_doc, test_id=str(doc['_id']), title=doc.get('title'))
    return doc


async def update_test(test_id: uuid.UUID, payload: TestCreate, user: dict) -> dict:
    tests = get_db()['tests']
    existing = await tests.find_one({'_id': test_id, **_ownership_filter(user)})
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Тест не найден')

    # Опубликованный тест неизменяем: иначе правки вопросов/вариантов рвут
    # связь с уже сохранёнными попытками (в них хранятся id вопросов и ответов).
    if existing.get('status') == TestStatus.PUBLISHED.value:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            'Опубликованный тест нельзя редактировать. Снимите его с публикации, чтобы изменить.',
        )

    # Защита от затирания: если клиент прислал версию, а на сервере документ
    # успели изменить (другая вкладка/устройство) — отдаём 409 Conflict.
    if payload.expected_updated_at is not None:
        current = existing.get('updated_at') or existing.get('created_at')
        # нормализуем tz: из Mongo может прийти naive datetime
        if current is not None and current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        expected = payload.expected_updated_at
        if expected.tzinfo is None:
            expected = expected.replace(tzinfo=timezone.utc)
        if current is not None and expected < current:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                'Тест был изменён в другом окне. Загрузите актуальную версию.',
            )

    doc: dict[str, Any] = Test(
        id=test_id,
        title=payload.title,
        description=payload.description,
        author=Author(**existing['author']),
        status=payload.status,
        public_token=existing['public_token'],
        questions=payload.questions,
        created_at=existing['created_at'],
    ).model_dump()
    doc['_id'] = doc.pop('id')
    doc['status'] = payload.status.value
    doc['author'] = existing['author']  # не трогаем снимок автора
    doc['updated_at'] = datetime.now(timezone.utc)

    await tests.replace_one({'_id': test_id}, doc)

    # Файлы изображений, которые больше нигде не используются, удаляем сразу —
    # хранилище ограничено. Считаем только id, оставшиеся в НОВОЙ версии теста.
    await _cleanup_orphan_media(existing, doc)
    return doc


def _collect_image_ids(doc: dict) -> set:
    result: set = set()
    for q in doc.get('questions', []):
        for i in q.get('image_ids', []) or []:
            result.add(i)
    return result


async def _cleanup_orphan_media(old_doc: dict, new_doc: dict) -> None:
    """Удаляет картинки, которые были в тесте, но исчезли из новой версии."""
    from services.media_service import delete_media_files

    old_ids = _collect_image_ids(old_doc)
    new_ids = _collect_image_ids(new_doc)
    orphans = list(old_ids - new_ids)
    if orphans:
        await delete_media_files(orphans)


async def list_user_tests(user: dict) -> list[TestSummary]:
    cursor = get_db()['tests'].find(_ownership_filter(user)).sort('created_at', -1)
    result: list[TestSummary] = []
    async for doc in cursor:
        published = doc['status'] == TestStatus.PUBLISHED.value
        result.append(TestSummary(
            id=str(doc['_id']),
            title=doc['title'],
            status=doc['status'],
            public_token=doc.get('public_token') if published else None,
            questions_count=len(doc.get('questions', [])),
        ))
    return result


async def get_owned_test(test_id: uuid.UUID, user: dict) -> dict:
    doc = await get_db()['tests'].find_one({'_id': test_id, **_ownership_filter(user)})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Тест не найден')
    return doc


def test_to_detail(doc: dict) -> TestDetail:
    return TestDetail(
        id=str(doc['_id']),
        title=doc['title'],
        description=doc.get('description'),
        status=doc['status'],
        public_token=doc['public_token'],
        questions=doc.get('questions', []),
        updated_at=doc.get('updated_at') or doc.get('created_at'),
    )


async def delete_test(test_id: uuid.UUID, user: dict) -> None:
    db = get_db()
    tests = db['tests']
    existing = await tests.find_one({'_id': test_id, **_ownership_filter(user)})
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Тест не найден')

    # каскадно удаляем попытки (ПДн участников не остаются висеть)
    attempts_res = await db['attempts'].delete_many({'test_id': test_id})
    # …и изображения вопросов (иначе занимают место впустую)
    from services.media_service import delete_media_files
    await delete_media_files(list(_collect_image_ids(existing)))
    await tests.delete_one({'_id': test_id})

    audit(
        'test.deleted',
        actor=user,
        test_id=str(test_id),
        title=existing.get('title'),
        public_token=existing.get('public_token'),
        author_id=str(existing.get('author', {}).get('user_id')),
        attempts_deleted=attempts_res.deleted_count,
    )


async def set_status(test_id: uuid.UUID, user: dict, new_status: TestStatus) -> dict:
    tests = get_db()['tests']
    res = await tests.find_one_and_update(
        {'_id': test_id, **_ownership_filter(user)},
        {'$set': {'status': new_status.value, 'updated_at': datetime.now(timezone.utc)}},
        return_document=True,
    )
    if res is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Тест не найден')
    audit(
        'test.status_changed',
        actor=user,
        test_id=str(test_id),
        title=res.get('title'),
        status=new_status.value,
    )
    return res


async def get_published_by_token(token: str) -> dict:
    doc = await get_db()['tests'].find_one(
        {'public_token': token, 'status': TestStatus.PUBLISHED.value}
    )
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Тест не найден или не опубликован')
    return doc


def test_to_public(doc: dict) -> TestPublic:
    """Скрываем правильные ответы от проходящего."""
    questions: list[QuestionPublic] = []
    for q in doc.get('questions', []):
        right = [p['right'] for p in q.get('pairs', [])]
        left = [p['left'] for p in q.get('pairs', [])]
        questions.append(QuestionPublic(
            id=str(q['id']),
            type=q['type'],
            text=q.get('text', ''),
            required=q.get('required', False),
            answers=[AnswerPublic(id=str(a['id']), text=a['text']) for a in q.get('answers', [])],
            pairs_left=left,
            pairs_right=right,
            image_urls=[f'/api/media/{i}' for i in q.get('image_ids', [])],
        ))
    return TestPublic(
        id=str(doc['_id']),
        title=doc['title'],
        description=doc.get('description'),
        questions=questions,
    )

