"""Тесты ограничителя частоты попыток входа."""
import pytest

from services import ratelimit


@pytest.fixture(autouse=True)
def clean_state():
    ratelimit._fails.clear()
    ratelimit._locked_until.clear()
    yield
    ratelimit._fails.clear()
    ratelimit._locked_until.clear()


def test_no_limit_initially():
    ratelimit.check_and_raise('k1')  # не должно бросать


def test_blocks_after_max_fails():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.register_failure('k1')
    with pytest.raises(ratelimit.TooManyAttempts) as exc:
        ratelimit.check_and_raise('k1')
    assert exc.value.retry_after >= 1


def test_reset_clears():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.register_failure('k2')
    ratelimit.reset('k2')
    ratelimit.check_and_raise('k2')  # после сброса не блокирован


def test_keys_are_isolated():
    for _ in range(ratelimit.MAX_FAILS):
        ratelimit.register_failure('a')
    ratelimit.check_and_raise('b')  # другой ключ не заблокирован
    with pytest.raises(ratelimit.TooManyAttempts):
        ratelimit.check_and_raise('a')


def test_below_threshold_no_block():
    for _ in range(ratelimit.MAX_FAILS - 1):
        ratelimit.register_failure('c')
    ratelimit.check_and_raise('c')  # ещё не достигли лимита


def test_retry_after_message():
    err = ratelimit.TooManyAttempts(42.7)
    assert err.retry_after == 42
    assert '42' in str(err)
