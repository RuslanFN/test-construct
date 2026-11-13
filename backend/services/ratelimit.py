"""Простое ограничение частоты попыток входа (in-memory).

Защита от перебора паролей. Работает в пределах одного процесса uvicorn.
Для нескольких реплик/воркеров нужен внешний счётчик (Redis) — см. примечание.
"""
import time
from collections import defaultdict, deque

# Параметры (можно вынести в config при необходимости)
MAX_FAILS = 5             # максимум неудачных попыток
WINDOW_SECONDS = 300      # окно наблюдения (5 минут)
LOCK_SECONDS = 300        # длительность блокировки после превышения

# ключ -> список временных меток неудачных попыток
_fails: dict[str, deque[float]] = defaultdict(deque)
# ключ -> до какого времени блокировка
_locked_until: dict[str, float] = {}


def _now() -> float:
    return time.monotonic()


def check_and_raise(key: str) -> None:
    """Вызывать перед проверкой пароля. Бросает, если ключ заблокирован."""
    now = _now()
    until = _locked_until.get(key)
    if until and until > now:
        raise TooManyAttempts(until - now)
    # почистить старое
    _prune(key, now)


def register_failure(key: str) -> None:
    """Вызывать при неудачном входе. Блокирует ключ при превышении лимита."""
    now = _now()
    dq = _fails[key]
    dq.append(now)
    _prune(key, now)
    if len(dq) >= MAX_FAILS:
        _locked_until[key] = now + LOCK_SECONDS
        dq.clear()


def reset(key: str) -> None:
    """Сбросить счётчик (успешный вход)."""
    _fails.pop(key, None)
    _locked_until.pop(key, None)


def _prune(key: str, now: float) -> None:
    dq = _fails.get(key)
    if not dq:
        return
    cutoff = now - WINDOW_SECONDS
    while dq and dq[0] < cutoff:
        dq.popleft()


class TooManyAttempts(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = max(1, int(retry_after))
        super().__init__(f'Слишком много попыток. Повторите через {self.retry_after} сек.')
