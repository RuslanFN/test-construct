"""Ограничение частоты чувствительных операций (login / register / submit).

In-memory: работает в пределах одного процесса uvicorn. Проект сейчас
развёрнут в одном экземпляре — этого достаточно. Для нескольких реплик
понадобится внешний счётчик (Redis).

Ключи независимые, чтобы лимит нельзя было обойти, меняя вторую часть:
- 'ip:<ip>'            — активность с одного IP (антиспам / антиперебор логинов);
- 'user:<username>'    — попытки входа в один аккаунт (перебор пароля с разных IP);
- 'reg:<username>'     — заявки на регистрацию одного логина;
- 'test:<ip>|<token>'  — прохождения одного теста с одного IP (анти-накрутка);
- 'submit-ip:<ip>'     — суммарные отправки прохождений с одного IP.
"""
import time
from collections import defaultdict, deque

# Дефолтные лимиты для входа
MAX_FAILS = 5              # неудач до блокировки
WINDOW_SECONDS = 300       # окно наблюдения, сек
BASE_LOCK_SECONDS = 60     # первая блокировка, сек
MAX_LOCK_SECONDS = 900     # потолок экспоненциального роста, сек

# ключ -> временные метки операций в текущем окне
_hits: dict[str, deque[float]] = defaultdict(deque)
# ключ -> до какого времени блокировка (monotonic)
_locked_until: dict[str, float] = {}
# ключ -> сколько раз уже блокировали (для роста блокировки)
_penalty: dict[str, int] = defaultdict(int)


def _now() -> float:
    return time.monotonic()


def keys_login(ip: str, username: str) -> tuple[str, ...]:
    """Вход: лимит глобально по IP и глобально по логину."""
    return (f'ip:{ip}', f'user:{username.strip().lower()}')


def keys_register(ip: str, username: str) -> tuple[str, ...]:
    """Регистрация: лимит по IP и по логину (анти-спам заявками)."""
    return (f'ip:{ip}', f'reg:{username.strip().lower()}')


def keys_captcha(ip: str) -> tuple[str, ...]:
    """Выдача задачи «я не робот»: лимит по IP (анти-спам запросами задач)."""
    return (f'captcha:{ip}',)


def keys_submit(ip: str, public_token: str) -> tuple[str, ...]:
    """Прохождение теста: лимит по паре IP|public_token и суммарно по IP."""
    return (f'test:{ip}|{public_token}', f'submit-ip:{ip}')


def check(*keys: str) -> None:
    """Проверить, не заблокирован ли субъект. Бросает TooManyAttempts."""
    until = remaining(*keys)
    if until > 0:
        raise TooManyAttempts(until)


def hit(
    *keys: str,
    window: int = WINDOW_SECONDS,
    limit: int = MAX_FAILS,
) -> None:
    """Учесть одну операцию. При превышении лимита блокирует ключ.

    Длительность блокировки растёт экспоненциально при повторных нарушениях
    (BASE_LOCK_SECONDS -> 2x -> 4x ...), но не больше MAX_LOCK_SECONDS.
    """
    now = _now()
    for key in keys:
        dq = _hits[key]
        dq.append(now)
        _prune(key, window)
        if len(dq) >= limit:
            _penalty[key] += 1
            lock = min(BASE_LOCK_SECONDS * (2 ** (_penalty[key] - 1)), MAX_LOCK_SECONDS)
            _locked_until[key] = now + lock
            dq.clear()


def reset(*keys: str) -> None:
    """Сбросить счётчики и блокировки (например, после успешного входа)."""
    for key in keys:
        _hits.pop(key, None)
        _locked_until.pop(key, None)
        _penalty.pop(key, None)


def _reset_all() -> None:
    """Сбросить всё состояние целиком (для тестов / ручной аварийной очистки)."""
    _hits.clear()
    _locked_until.clear()
    _penalty.clear()


def remaining(*keys: str) -> float:
    """Сколько секунд ещё действует блокировка (0 — не заблокировано)."""
    now = _now()
    return max(
        (_locked_until[k] - now for k in keys if _locked_until.get(k, 0) > now),
        default=0.0,
    )


def count(*keys: str, window: int = WINDOW_SECONDS) -> int:
    """Сколько операций по ключу за окно (макс. по всем ключам).

    Нужно, например, чтобы решить, требовать ли капчу: если по IP или логину
    уже было N неудачных входов — капча обязательна.
    """
    best = 0
    for key in keys:
        _prune(key, window)
        best = max(best, len(_hits.get(key, ())))
    return best


def _prune(key: str, window: int) -> None:
    dq = _hits.get(key)
    if not dq:
        return
    cutoff = _now() - window
    while dq and dq[0] < cutoff:
        dq.popleft()


class TooManyAttempts(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = max(1, int(retry_after))
        super().__init__(f'Слишком много попыток. Повторите через {self.retry_after} сек.')
