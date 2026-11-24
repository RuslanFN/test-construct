"""Тесты арифметической капчи и лимитера (без БД и сети)."""
import time

import pytest

import config  # noqa: F401  (нужен для jwt_secret при импорте captcha)
from services import captcha, ratelimit

WORDS = {
    'ноль': 0, 'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6,
    'семь': 7, 'восемь': 8, 'девять': 9, 'десять': 10, 'одиннадцать': 11,
    'двенадцать': 12, 'тринадцать': 13, 'четырнадцать': 14, 'пятнадцать': 15,
    'шестнадцать': 16, 'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
    'двадцать': 20,
}


def _solve(question: str) -> str:
    a, _, b = question.partition(' плюс ')
    return str(WORDS[a] + WORDS[b])


@pytest.fixture(autouse=True)
def no_min_seconds(monkeypatch):
    """В тестах «слишком быстрый» порог отключён — иначе истечение 1 сек ловится медленно."""
    monkeypatch.setattr(captcha, 'MIN_SECONDS', 0.0)


def test_captcha_question_is_words():
    task = captcha.issue()
    assert ' плюс ' in task['question']
    # в вопросе нет цифр — только слова
    assert not any(ch.isdigit() for ch in task['question'])


def test_captcha_valid_answer():
    task = captcha.issue()
    assert captcha.verify(task['token'], _solve(task['question'])) is True


def test_captcha_wrong_answer():
    task = captcha.issue()
    assert captcha.verify(task['token'], '99999') is False


def test_captcha_one_time():
    task = captcha.issue()
    answer = _solve(task['question'])
    assert captcha.verify(task['token'], answer) is True
    # повторное использование того же токена запрещено
    assert captcha.verify(task['token'], answer) is False


def test_captcha_tampered_token():
    task = captcha.issue()
    answer = _solve(task['question'])
    assert captcha.verify(task['token'][:-2] + 'aa', answer) is False


def test_captcha_missing():
    assert captcha.verify(None, '5') is False
    task = captcha.issue()
    assert captcha.verify(task['token'], None) is False


def test_captcha_honeypot_filled_rejected():
    """Заполненная ловушка — отказ даже при верном ответе."""
    task = captcha.issue()
    answer = _solve(task['question'])
    assert captcha.verify(task['token'], answer, 'spam@bot.example') is False
    # токен не «сгорел» — он не был принят
    assert captcha.verify(task['token'], answer, None) is True


def test_captcha_empty_honeypot_ok():
    task = captcha.issue()
    assert captcha.verify(task['token'], _solve(task['question']), '') is True


def test_captcha_too_fast_rejected(monkeypatch):
    """Ответ быстрее порога (мгновенный автоответ) отклоняется."""
    monkeypatch.setattr(captcha, 'MIN_SECONDS', 5.0)
    task = captcha.issue()
    # только что выдан (iat == now) → elapsed 0 < 5
    assert captcha.verify(task['token'], _solve(task['question'])) is False


def test_captcha_expired_rejected():
    """Просроченный токен (exp в прошлом) отклоняется, даже при верном ответе."""
    import base64
    import json

    answer = 5
    payload = json.dumps(
        {'ans': answer, 'iat': int(time.time()) - 1000,
         'exp': int(time.time()) - 10, 'jti': 'x'},
        separators=(',', ':'), sort_keys=True,
    ).encode('utf-8')
    token = (base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=')
             + '.' + captcha._sign(payload))
    assert captcha.verify(token, str(answer)) is False
