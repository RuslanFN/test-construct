"""Тесты ограничителя частоты попыток (актуальный API services.ratelimit)."""
import pytest

from services import ratelimit


@pytest.fixture(autouse=True)
def clean_state():
    # Сбрасываем состояние публичным API (внутренние структуры — деталь реализации).
    ratelimit.reset('k1', 'k2', 'a', 'b', 'c')
    yield
    ratelimit.reset('k1', 'k2', 'a', 'b', 'c')
def test_no_limit_initially():
    ratelimit.check('k1')  # не должно бросать


def test_blocks_after_max_fails():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.hit('k1')
    with pytest.raises(ratelimit.TooManyAttempts) as exc:
        ratelimit.check('k1')
    assert exc.value.retry_after >= 1


def test_reset_clears():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.hit('k2')
    ratelimit.reset('k2')
    ratelimit.check('k2')  # после сброса не блокирован


def test_keys_are_isolated():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.hit('a')
    ratelimit.check('b')  # другой ключ не заблокирован
    with pytest.raises(ratelimit.TooManyAttempts):
        ratelimit.check('a')


def test_below_threshold_no_block():
    for _ in range(ratelimit.MAX_FAILS - 1):
        ratelimit.hit('c')
    ratelimit.check('c')  # ещё не достигли лимита


def test_retry_after_message():
    err = ratelimit.TooManyAttempts(42.7)
    assert err.retry_after == 42
    assert '42' in str(err)

