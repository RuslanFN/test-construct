"""Тесты сервиса прохождения: проверка ответов, подсчёт, детали, Excel."""
import uuid

import pytest
from fastapi import HTTPException

from schemas.attempt import AttemptSubmit, GivenAnswer, ParticipantIn
from services import attempt_service
from tests.conftest import make_question


def _participant(**over):
    data = dict(
        last_name='Иванов',
        first_name='Иван',
        middle_name=None,
        certificate_number='1234567890',
    )
    data.update(over)
    return ParticipantIn(**data)


def _test_doc(questions):
    return {
        '_id': uuid.uuid4(),
        'title': 'Тест',
        'questions': questions,
    }


def _one_question():
    """Вопрос с одним правильным ответом. Возвращает (question, correct_id, wrong_id)."""
    correct_id = str(uuid.uuid4())
    wrong_id = str(uuid.uuid4())
    q = make_question('one', answers=[
        {'id': correct_id, 'text': 'Верно', 'is_correct': True},
        {'id': wrong_id, 'text': 'Неверно', 'is_correct': False},
    ])
    return q, correct_id, wrong_id


# ---------- one ----------

async def test_submit_one_correct(fake_db):
    q, correct, wrong = _one_question()
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[correct])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1
    assert result.total == 1
    assert result.percent == 100.0
    assert result.results[0].is_correct is True


async def test_submit_one_incorrect(fake_db):
    q, correct, wrong = _one_question()
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[wrong])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 0
    assert result.results[0].is_correct is False


async def test_submit_one_no_answer(fake_db):
    q, correct, wrong = _one_question()
    doc = _test_doc([q])
    payload = AttemptSubmit(participant=_participant(), answers=[])
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 0
    assert result.results[0].is_correct is False


# ---------- some ----------

async def test_submit_some_all_correct(fake_db):
    a1, a2 = str(uuid.uuid4()), str(uuid.uuid4())
    q = make_question('some', answers=[
        {'id': a1, 'text': 'A', 'is_correct': True},
        {'id': a2, 'text': 'B', 'is_correct': True},
        {'id': str(uuid.uuid4()), 'text': 'C', 'is_correct': False},
    ])
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[a1, a2])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1


async def test_submit_some_partial_wrong(fake_db):
    a1 = str(uuid.uuid4())
    q = make_question('some', answers=[
        {'id': a1, 'text': 'A', 'is_correct': True},
        {'id': str(uuid.uuid4()), 'text': 'B', 'is_correct': True},
    ])
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[a1])],  # выбрал не все
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 0


# ---------- text ----------

async def test_submit_text_correct_case_insensitive(fake_db):
    q = make_question('text', answers=[
        {'id': str(uuid.uuid4()), 'text': 'Москва', 'is_correct': True},
    ])
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=['  москва '])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1


async def test_submit_text_incorrect(fake_db):
    q = make_question('text', answers=[
        {'id': str(uuid.uuid4()), 'text': 'Москва', 'is_correct': True},
    ])
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=['Питер'])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 0


# ---------- match ----------

async def test_submit_match_correct(fake_db):
    pairs = [
        {'id': str(uuid.uuid4()), 'left': 'A', 'right': '1'},
        {'id': str(uuid.uuid4()), 'left': 'B', 'right': '2'},
    ]
    q = make_question('match', pairs=pairs)
    doc = _test_doc([q])
    # left0->right0, left1->right1
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], matches=[(0, 0), (1, 1)])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1


async def test_submit_match_incorrect(fake_db):
    pairs = [
        {'id': str(uuid.uuid4()), 'left': 'A', 'right': '1'},
        {'id': str(uuid.uuid4()), 'left': 'B', 'right': '2'},
    ]
    q = make_question('match', pairs=pairs)
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], matches=[(0, 1), (1, 0)])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 0


# ---------- обязательные вопросы ----------

async def test_required_question_unanswered_400(fake_db):
    q = make_question('one', required=True)
    doc = _test_doc([q])
    payload = AttemptSubmit(participant=_participant(), answers=[])
    with pytest.raises(HTTPException) as e:
        await attempt_service.submit_attempt(doc, payload, None)
    assert e.value.status_code == 400


async def test_required_question_answered_ok(fake_db):
    q, correct, _ = _one_question()
    q['required'] = True
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[correct])],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1


async def test_required_match_all_pairs_needed(fake_db):
    pairs = [
        {'id': str(uuid.uuid4()), 'left': 'A', 'right': '1'},
        {'id': str(uuid.uuid4()), 'left': 'B', 'right': '2'},
    ]
    q = make_question('match', pairs=pairs, required=True)
    doc = _test_doc([q])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], matches=[(0, 0)])],  # только 1 из 2
    )
    with pytest.raises(HTTPException) as e:
        await attempt_service.submit_attempt(doc, payload, None)
    assert e.value.status_code == 400


# ---------- подсчёт процентов и сохранение ----------

async def test_percent_and_persistence(fake_db):
    q1, c1, _ = _one_question()
    q2, c2, w2 = _one_question()
    doc = _test_doc([q1, q2])
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[
            GivenAnswer(question_id=q1['id'], selected=[c1]),  # верно
            GivenAnswer(question_id=q2['id'], selected=[w2]),  # неверно
        ],
    )
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.score == 1
    assert result.total == 2
    assert result.percent == 50.0
    # попытка сохранена в БД
    assert len(fake_db['attempts']._docs) == 1
    saved = fake_db['attempts']._docs[0]
    assert saved['score'] == 1
    assert saved['participant']['last_name'] == 'Иванов'
    # веса у question_id в исходном формате
    assert all('question_id' in r for r in saved['results'])


async def test_empty_questions_percent_zero(fake_db):
    doc = _test_doc([])
    payload = AttemptSubmit(participant=_participant(), answers=[])
    result = await attempt_service.submit_attempt(doc, payload, None)
    assert result.total == 0
    assert result.percent == 0.0


async def test_submit_with_user_id(fake_db):
    q, c, _ = _one_question()
    doc = _test_doc([q])
    uid = uuid.uuid4()
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id=q['id'], selected=[c])],
    )
    await attempt_service.submit_attempt(doc, payload, uid)
    assert fake_db['attempts']._docs[0]['user_id'] == uid


# ---------- list_test_attempts ----------

async def test_list_test_attempts_and_average(fake_db):
    test_id = uuid.uuid4()
    fake_db['attempts']._docs.append({
        '_id': uuid.uuid4(), 'test_id': test_id, 'score': 1, 'total': 2, 'percent': 50.0,
        'participant': {'last_name': 'A', 'first_name': 'B', 'certificate_number': '1234567890'},
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
    })
    fake_db['attempts']._docs.append({
        '_id': uuid.uuid4(), 'test_id': test_id, 'score': 2, 'total': 2, 'percent': 100.0,
        'participant': {'last_name': 'C', 'first_name': 'D', 'certificate_number': '0987654321'},
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
    })
    out = await attempt_service.list_test_attempts({'_id': test_id, 'title': 'T'})
    assert out.attempts_count == 2
    assert out.average_percent == 75.0


async def test_list_test_attempts_empty(fake_db):
    out = await attempt_service.list_test_attempts({'_id': uuid.uuid4(), 'title': 'T'})
    assert out.attempts_count == 0
    assert out.average_percent == 0.0


# ---------- get_attempt_detail ----------

async def test_get_attempt_detail_not_found(fake_db):
    with pytest.raises(HTTPException) as e:
        await attempt_service.get_attempt_detail({'_id': uuid.uuid4(), 'questions': []}, uuid.uuid4())
    assert e.value.status_code == 404


async def test_get_attempt_detail_with_snapshot(fake_db):
    test_id = uuid.uuid4()
    qid = str(uuid.uuid4())
    attempt_id = uuid.uuid4()
    fake_db['attempts']._docs.append({
        '_id': attempt_id, 'test_id': test_id, 'test_title': 'T',
        'score': 1, 'total': 1, 'percent': 100.0,
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
        'results': [{
            'question_id': qid, 'is_correct': True,
            'text': 'Вопрос?', 'given_texts': ['Верно'], 'correct_texts': ['Верно'],
            'given_answer': [], 'correct_answer': [],
        }],
    })
    detail = await attempt_service.get_attempt_detail(
        {'_id': test_id, 'title': 'T', 'questions': []}, attempt_id
    )
    assert detail.questions[0].text == 'Вопрос?'
    assert detail.questions[0].given == ['Верно']
    assert detail.questions[0].is_correct is True


# ---------- xlsx ----------

async def test_attempts_to_xlsx_returns_bytes(fake_db):
    test_id = uuid.uuid4()
    fake_db['attempts']._docs.append({
        '_id': uuid.uuid4(), 'test_id': test_id, 'score': 1, 'total': 1, 'percent': 100.0,
        'participant': {'last_name': 'Иванов', 'first_name': 'Иван', 'middle_name': None,
                        'certificate_number': '1234567890'},
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
    })
    data = await attempt_service.attempts_to_xlsx({'_id': test_id, 'title': 'T'})
    assert isinstance(data, bytes)
    assert len(data) > 0
    # xlsx — это zip-формат (начинается с PK)
    assert data[:2] == b'PK'
