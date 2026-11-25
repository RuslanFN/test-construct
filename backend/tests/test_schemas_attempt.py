"""Тесты валидации схемы участника и ответов при прохождении."""
import pytest
from pydantic import ValidationError

from schemas.attempt import AttemptSubmit, GivenAnswer, ParticipantIn


def _participant(**over):
    data = dict(
        last_name='Иванов',
        first_name='Иван',
        middle_name=None,
        certificate_number='1234567890',
        pd_consent=True,
    )
    data.update(over)
    return data


def test_valid_participant():
    p = ParticipantIn(**_participant())
    assert p.certificate_number == '1234567890'


def test_last_name_empty():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(last_name='  '))
    assert 'обязательно' in str(e.value)


def test_last_name_too_long():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(last_name='я' * 31))
    assert 'слишком длинное' in str(e.value)


def test_first_name_too_long():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(first_name='я' * 31))
    assert 'слишком длинное' in str(e.value)


def test_middle_name_optional():
    p = ParticipantIn(**_participant(middle_name=None))
    assert p.middle_name is None


def test_middle_name_too_long():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(middle_name='о' * 31))
    assert 'слишком длинное' in str(e.value)


def test_certificate_wrong_digits():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(certificate_number='12345'))
    assert '10 цифр' in str(e.value)


def test_certificate_non_numeric():
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(certificate_number='12345abcde'))
    assert '10 цифр' in str(e.value)


def test_consent_required():
    """Без согласия на обработку ПДн участник не проходит валидацию."""
    with pytest.raises(ValidationError) as e:
        ParticipantIn(**_participant(pd_consent=False))
    assert 'согласие' in str(e.value)


def test_consent_missing_defaults_to_false_and_rejected():
    """Не переданное поле тоже отклоняется (чекбокс не отмечен по умолчанию)."""
    data = _participant()
    data.pop('pd_consent')
    with pytest.raises(ValidationError):
        ParticipantIn(**data)


def test_attempt_submit_structure():
    payload = AttemptSubmit(
        participant=_participant(),
        answers=[GivenAnswer(question_id='q1', selected=['a1'])],
    )
    assert payload.answers[0].question_id == 'q1'


def test_given_answer_defaults():
    g = GivenAnswer(question_id='q1')
    assert g.selected == []
    assert g.matches == []
