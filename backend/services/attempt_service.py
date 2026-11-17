import io
import uuid
from typing import Any

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Font

from db import get_db
from models.attempt import Attempt, Participant, QuestionResult
from models.question_type import QuestionType
from schemas.attempt import (
    AttemptDetail,
    AttemptResult,
    AttemptSubmit,
    AttemptSummary,
    GivenAnswer,
    ParticipantOut,
    QuestionDetail,
    QuestionResultOut,
    TestAttemptsOut,
)
from schemas.test import TestPublic


def _participant_out(p: dict | None) -> ParticipantOut | None:
    if not p:
        return None
    return ParticipantOut(
        last_name=p.get('last_name', ''),
        first_name=p.get('first_name', ''),
        middle_name=p.get('middle_name'),
        certificate_number=p.get('certificate_number', ''),
    )


def _correct_ids(question: dict) -> list[str]:
    return sorted(str(a['id']) for a in question.get('answers', []) if a.get('is_correct'))


def _correct_matches(question: dict) -> list[str]:
    # правильные пары относительно порядка left->right индексов
    pairs = question.get('pairs', [])
    result = []
    for idx, pair in enumerate(pairs):
        result.append(f'{idx}:{pair["right"]}')
    return sorted(result)


def _given_matches(question: dict, given: GivenAnswer) -> list[str]:
    pairs = question.get('pairs', [])
    result = []
    for left_idx, right_idx in given.matches:
        if 0 <= left_idx < len(pairs) and 0 <= right_idx < len(pairs):
            result.append(f'{left_idx}:{pairs[right_idx]["right"]}')
    return sorted(result)


def _check_question(question: dict, given: GivenAnswer | None) -> QuestionResult:
    qtype = question['type']
    qid = question['id']
    qtext = question.get('text', '')

    if given is None:
        given = GivenAnswer(question_id=str(qid))
    if qtype in (QuestionType.ONE.value, QuestionType.SOME.value):
        given_ids = sorted(given.selected)
        correct = _correct_ids(question)
        is_correct = given_ids == correct
        return QuestionResult(
            question_id=qid, is_correct=is_correct,
            text=qtext,
            given_texts=[_answer_text_by_id(question, g) for g in given_ids],
            correct_texts=[_answer_text_by_id(question, c) for c in correct],
            given_answer=given_ids, correct_answer=correct,
        )

    if qtype == QuestionType.TEXT.value:
        # сравниваем с текстом правильного варианта (answers[0].text)
        correct_text = ''
        for a in question.get('answers', []):
            if a.get('is_correct'):
                correct_text = a['text']
                break
        given_text = (given.selected[0] if given.selected else '').strip().lower()
        is_correct = given_text == correct_text.strip().lower() and correct_text != ''
        return QuestionResult(
            question_id=qid, is_correct=is_correct,
            text=qtext,
            given_texts=[given_text] if given_text else [],
            correct_texts=[correct_text] if correct_text else [],
            given_answer=[given_text], correct_answer=[correct_text],
        )

    # MATCH
    correct = _correct_matches(question)
    given_m = _given_matches(question, given)
    return QuestionResult(
        question_id=qid, is_correct=given_m == correct,
        text=qtext,
        given_texts=_readable_given_match(question, given_m),
        correct_texts=_readable_correct(question, correct),
        given_answer=given_m, correct_answer=correct,
    )


async def submit_attempt(
    test_doc: dict,
    payload: AttemptSubmit,
    user_id: uuid.UUID | None,
) -> AttemptResult:
    by_id = {a.question_id: a for a in payload.answers}
    questions = test_doc.get('questions', [])

    # валидация обязательных вопросов
    for q in questions:
        if not q.get('required'):
            continue
        given = by_id.get(str(q['id']))
        answered = False
        if given is not None:
            if q['type'] == QuestionType.MATCH.value:
                # должны быть заполнены все пары
                answered = len(given.matches) >= len(q.get('pairs', [])) and len(q.get('pairs', [])) > 0
            else:
                answered = any((v or '').strip() if isinstance(v, str) else True
                               for v in given.selected)
        if not answered:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                'Не отвечены обязательные вопросы',
            )

    results = [_check_question(q, by_id.get(str(q['id']))) for q in questions]
    # сопоставим ввод по исходному id (uuid) вопроса
    for q, r in zip(questions, results):
        r.question_id = q['id']

    total = len(questions)
    score = sum(1 for r in results if r.is_correct)
    percent = round(score / total * 100, 2) if total else 0.0

    attempt = Attempt(
        test_id=test_doc['_id'],
        test_title=test_doc['title'],
        user_id=user_id,
        participant=Participant(
            last_name=payload.participant.last_name,
            first_name=payload.participant.first_name,
            middle_name=payload.participant.middle_name,
            certificate_number=payload.participant.certificate_number,
        ),
        score=score,
        total=total,
        percent=percent,
        results=results,
    )
    doc: dict[str, Any] = attempt.model_dump()
    doc['_id'] = doc.pop('id')
    await get_db()['attempts'].insert_one(doc)

    return AttemptResult(
        id=str(attempt.id),
        test_id=str(attempt.test_id),
        test_title=attempt.test_title,
        score=attempt.score,
        total=attempt.total,
        percent=attempt.percent,
        results=[
            QuestionResultOut(
                question_id=str(r.question_id),
                is_correct=r.is_correct,
                given_answer=r.given_answer,
                correct_answer=r.correct_answer,
            )
            for r in attempt.results
        ],
        created_at=attempt.created_at,
    )


async def list_test_attempts(test_doc: dict) -> TestAttemptsOut:
    """Все попытки прохождения теста (для владельца) + сводка."""
    cursor = get_db()['attempts'].find({'test_id': test_doc['_id']}).sort('created_at', -1)
    attempts: list[AttemptSummary] = []
    total_percent = 0.0
    async for doc in cursor:
        attempts.append(AttemptSummary(
            id=str(doc['_id']),
            test_id=str(doc['test_id']),
            user_id=str(doc['user_id']) if doc.get('user_id') else None,
            guest_name=doc.get('guest_name'),
            participant=_participant_out(doc.get('participant')),
            score=doc['score'],
            total=doc['total'],
            percent=doc['percent'],
            created_at=doc['created_at'],
        ))
        total_percent += doc['percent']

    count = len(attempts)
    average = round(total_percent / count, 2) if count else 0.0
    return TestAttemptsOut(
        test_id=str(test_doc['_id']),
        test_title=test_doc['title'],
        attempts=attempts,
        attempts_count=count,
        average_percent=average,
    )


def _answer_text_by_id(question: dict, answer_id: str) -> str:
    for a in question.get('answers', []):
        if str(a['id']) == str(answer_id):
            return a['text']
    # вариант удалён из теста после прохождения — не показываем сырой UUID
    return '— вариант удалён —'


def _readable_given(question: dict, given: list[str]) -> list[str]:
    """given хранится как id вариантов (one/some) или текст (text)."""
    qtype = question['type']
    if qtype in (QuestionType.ONE.value, QuestionType.SOME.value):
        return [_answer_text_by_id(question, g) for g in given]
    # text: given = [текст]
    return [g for g in given if g]


def _readable_correct(question: dict, correct: list[str]) -> list[str]:
    qtype = question['type']
    if qtype in (QuestionType.ONE.value, QuestionType.SOME.value):
        return [_answer_text_by_id(question, c) for c in correct]
    if qtype == QuestionType.TEXT.value:
        return [c for c in correct if c]
    # MATCH: "leftIdx:rightText" -> "leftText → rightText"
    pairs = question.get('pairs', [])
    out = []
    for item in correct:
        try:
            left_idx, right_text = item.split(':', 1)
            li = int(left_idx)
            left_text = pairs[li]['left'] if 0 <= li < len(pairs) else left_idx
            out.append(f'{left_text} → {right_text}')
        except (ValueError, IndexError):
            out.append(item)
    return out


def _readable_given_match(question: dict, given: list[str]) -> list[str]:
    pairs = question.get('pairs', [])
    out = []
    for item in given:
        try:
            left_idx, right_text = item.split(':', 1)
            li = int(left_idx)
            left_text = pairs[li]['left'] if 0 <= li < len(pairs) else left_idx
            out.append(f'{left_text} → {right_text}')
        except (ValueError, IndexError):
            out.append(item)
    return out


async def get_attempt_detail(test_doc: dict, attempt_id: uuid.UUID) -> AttemptDetail:
    doc = await get_db()['attempts'].find_one({'_id': attempt_id, 'test_id': test_doc['_id']})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Попытка не найдена')

    questions_by_id = {str(q['id']): q for q in test_doc.get('questions', [])}
    details: list[QuestionDetail] = []
    for r in doc.get('results', []):
        q = questions_by_id.get(str(r['question_id']))
        qtype = q['type'] if q else 'one'
        given = r.get('given_answer', [])
        correct = r.get('correct_answer', [])

        # Если в попытке есть снимок текстов — используем его. Тогда результат
        # не зависит от того, что правки/удаления были сделаны в тесте позже.
        has_snapshot = 'given_texts' in r and 'correct_texts' in r
        if has_snapshot:
            text = r.get('text', '')
            given_txt = r.get('given_texts', [])
            correct_txt = r.get('correct_texts', [])
            if q:
                qt = q.get('type')
                if qt:
                    qtype = qt
        elif q:
            text = q.get('text', '')
            if qtype == QuestionType.MATCH.value:
                given_txt = _readable_given_match(q, given)
            else:
                given_txt = _readable_given(q, given)
            correct_txt = _readable_correct(q, correct)
        else:
            text = ''
            given_txt, correct_txt = given, correct
        details.append(QuestionDetail(
            question_id=str(r['question_id']),
            type=qtype,
            text=text,
            is_correct=r['is_correct'],
            given=[g for g in given_txt if g],
            correct=correct_txt,
        ))

    return AttemptDetail(
        id=str(doc['_id']),
        test_id=str(doc['test_id']),
        test_title=doc['test_title'],
        guest_name=doc.get('guest_name'),
        participant=_participant_out(doc.get('participant')),
        user_id=str(doc['user_id']) if doc.get('user_id') else None,
        score=doc['score'],
        total=doc['total'],
        percent=doc['percent'],
        created_at=doc['created_at'],
        questions=details,
    )


async def attempts_to_xlsx(test_doc: dict) -> bytes:
    """Выгрузка всех попыток теста в Excel (.xlsx) для владельца."""
    wb = Workbook()
    ws = wb.active
    ws.title = 'Результаты'

    headers = [
        'Фамилия', 'Имя', 'Отчество', 'Номер сертификата',
        'Правильных', 'Всего', 'Процент', 'Время прохождения',
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    cursor = get_db()['attempts'].find({'test_id': test_doc['_id']}).sort('created_at', 1)
    async for doc in cursor:
        p = doc.get('participant') or {}
        created = doc['created_at']
        ws.append([
            p.get('last_name', '') or (doc.get('guest_name') or ''),
            p.get('first_name', ''),
            p.get('middle_name') or '',
            p.get('certificate_number', ''),
            doc['score'],
            doc['total'],
            doc['percent'],
            created.isoformat() if hasattr(created, 'isoformat') else created,
        ])

    # авто-ширина колонок
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


