"""Интеграционные тесты /api/public: получение теста по токену и прохождение."""
import uuid

from tests.conftest import make_question, make_test_doc


def _published_test_with_one_question(fake_db, token='publictok'):
    correct_id = str(uuid.uuid4())
    wrong_id = str(uuid.uuid4())
    q = make_question('one', answers=[
        {'id': correct_id, 'text': 'Верно', 'is_correct': True},
        {'id': wrong_id, 'text': 'Неверно', 'is_correct': False},
    ])
    doc = make_test_doc(
        author_id=uuid.uuid4(), status='published', public_token=token, questions=[q]
    )
    fake_db['tests']._docs.append(doc)
    return doc, q, correct_id, wrong_id


def _participant_payload():
    return {
        'last_name': 'Иванов',
        'first_name': 'Иван',
        'middle_name': None,
        'certificate_number': '1234567890',
    }


def test_get_public_test_hides_answers(api_client, fake_db):
    doc, q, correct, wrong = _published_test_with_one_question(fake_db)
    resp = api_client.get('/api/public/tests/publictok')
    assert resp.status_code == 200
    body = resp.json()
    assert body['title'] == doc['title']
    # нет поля is_correct
    assert 'is_correct' not in body['questions'][0]['answers'][0]


def test_get_public_test_unknown_404(api_client, fake_db):
    resp = api_client.get('/api/public/tests/nonexistent')
    assert resp.status_code == 404


def test_get_public_draft_404(api_client, fake_db):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=uuid.uuid4(), status='draft', public_token='drafttok')
    )
    resp = api_client.get('/api/public/tests/drafttok')
    assert resp.status_code == 404


def test_submit_correct(api_client, fake_db):
    doc, q, correct, wrong = _published_test_with_one_question(fake_db)
    resp = api_client.post(
        '/api/public/tests/publictok/submit',
        json={
            'participant': _participant_payload(),
            'answers': [{'question_id': q['id'], 'selected': [correct]}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body['score'] == 1
    assert body['percent'] == 100.0
    assert len(fake_db['attempts']._docs) == 1


def test_submit_incorrect(api_client, fake_db):
    doc, q, correct, wrong = _published_test_with_one_question(fake_db)
    resp = api_client.post(
        '/api/public/tests/publictok/submit',
        json={
            'participant': _participant_payload(),
            'answers': [{'question_id': q['id'], 'selected': [wrong]}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()['score'] == 0


def test_submit_invalid_participant_422(api_client, fake_db):
    _published_test_with_one_question(fake_db)
    bad = _participant_payload()
    bad['certificate_number'] = '123'
    resp = api_client.post(
        '/api/public/tests/publictok/submit',
        json={'participant': bad, 'answers': []},
    )
    assert resp.status_code == 422


def test_submit_to_draft_404(api_client, fake_db):
    fake_db['tests']._docs.append(
        make_test_doc(author_id=uuid.uuid4(), status='draft', public_token='drafttok')
    )
    resp = api_client.post(
        '/api/public/tests/drafttok/submit',
        json={'participant': _participant_payload(), 'answers': []},
    )
    assert resp.status_code == 404
