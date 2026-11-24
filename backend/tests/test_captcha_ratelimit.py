"""Тесты арифметической капчи и лимитера (без БД и сети)."""
import pytest

import config  # noqa: F401  (нужен для jwt_secret при импорте captcha)
from services import captcha, ratelimit


def _solve(question: str) -> str:
    a, _, b = question.partition(' + ')
    return str(int(a) + int(b))


def test_captcha_valid_answer():
    task = captcha.issue()
    assert '+' in task['question']
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


def test_ratelimit_blocks_and_resets():
    keys = ('test:limit-block',)
    ratelimit.reset(*keys)
    # 5 операций — лимит исчерпан, 6-я блокирует
    for _ in range(5):
        ratelimit.hit(*keys, limit=5, window=60)
    with pytest.raises(ratelimit.TooManyAttempts):
        ratelimit.check(*keys)
    ratelimit.reset(*keys)
    ratelimit.check(*keys)  # после сброса — свободно


def test_ratelimit_keys_are_independent():
    a, b = ('test:indep-a',), ('test:indep-b',)
    ratelimit.reset(*a, *b)
    for _ in range(5):
        ratelimit.hit(*a, limit=5, window=60)
    with pytest.raises(ratelimit.TooManyAttempts):
        ratelimit.check(*a)
    ratelimit.check(*b)  # другой ключ не заблокирован
    ratelimit.reset(*a, *b)


def test_ratelimit_count():
    keys = ('test:count',)
    ratelimit.reset(*keys)
    assert ratelimit.count(*keys, window=60) == 0
    ratelimit.hit(*keys, limit=100, window=60)
    ratelimit.hit(*keys, limit=100, window=60)
    assert ratelimit.count(*keys, window=60) == 2
    ratelimit.reset(*keys)
