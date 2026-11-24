"""Арифметическая капча «Я не робот» (без внешних сервисов, офлайн).

Как работает:
    1. Сервер генерирует пример (например, «7 + 3») и подписывает ответ+срок
       жизни HMAC-SHA256 на `config.secret_key`. Клиент получает вопрос и токен.
    2. Клиент присылает token + ответ. Сервер проверяет подпись, срок и ответ.
       Подделать ответ нельзя — подпись без секрета не пересчитать.
    3. Токен одноразовый (успешная проверка «сжигает» его до истечения TTL).

TTL ограничен, чтобы токен нельзя было переиспользовать; использованные
токены хранятся в памяти (как и rate limiting) — в пределах одного процесса.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

import config

# Время жизни задачи, сек
TTL_SECONDS = 180
# Предел результата примера (простые числа, чтобы считалось в голове)
_OPERANDS_MAX = 9
# Сколько использованных токенов держим в памяти (защита от разрастания)
_USED_SWEEP = 1000

# jti -> до какого времени (monotonic) держать как использованный
_used: dict[str, float] = {}


def _sign(payload: bytes) -> str:
    return hmac.new(
        config.secret_key.encode('utf-8'), payload, hashlib.sha256,
    ).hexdigest()


def issue() -> dict:
    """Сгенерировать задачу. Возвращает {'question': '7 + 3', 'token': '...'}."""
    a = secrets.randbelow(_OPERANDS_MAX) + 1
    b = secrets.randbelow(_OPERANDS_MAX) + 1
    answer = a + b
    jti = secrets.token_urlsafe(8)
    exp = int(time.time()) + TTL_SECONDS

    payload = json.dumps(
        {'a': a, 'b': b, 'ans': answer, 'exp': exp, 'jti': jti},
        separators=(',', ':'), sort_keys=True,
    ).encode('utf-8')
    token = base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=') + '.' + _sign(payload)
    return {'question': f'{a} + {b}', 'token': token}


def verify(token: str | None, answer: str | None) -> bool:
    """Проверить токен и ответ. Успешная проверка сжигает токен."""
    if not token or answer is None:
        return False
    try:
        raw, sig = token.rsplit('.', 1)
        padded = raw + '=' * (-len(raw) % 4)
        payload = base64.urlsafe_b64decode(padded.encode('ascii'))
    except (ValueError, TypeError):
        return False

    if not hmac.compare_digest(sig, _sign(payload)):
        return False

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return False

    if int(data.get('exp', 0)) < int(time.time()):
        return False

    jti = data.get('jti', '')
    if jti in _used:
        return False  # уже использован

    try:
        given = int(str(answer).strip())
    except (ValueError, TypeError):
        return False

    if given != int(data.get('ans', -1)):
        return False

    # Успех: помечаем одноразовым до истечения срока
    _used[jti] = time.monotonic() + TTL_SECONDS
    _sweep_used()
    return True


def _sweep_used() -> None:
    """Удаляем использованные токены, у которых истёк TTL."""
    if len(_used) < _USED_SWEEP:
        return
    now = time.monotonic()
    for jti in [k for k, until in _used.items() if until <= now]:
        _used.pop(jti, None)
