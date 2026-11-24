"""Арифметическая капча «Я не робот» словами (без внешних сервисов, офлайн).

Как работает:
    1. Сервер генерирует пример СЛОВАМИ (например, «семь плюс три») и подписывает
       правильный ответ + время выдачи + срок жизни HMAC-SHA256 на `secret_key`.
       Клиент получает вопрос и токен, а ответ вводит ЦИФРАМИ.
    2. Клиент присылает token + ответ. Сервер проверяет подпись, срок, «не слишком
       быстро» (защита от мгновенного автоответа) и ответ. Подделать нельзя —
       подпись без секрета не пересчитать.
    3. Токен одноразовый (успешная проверка «сжигает» его до истечения TTL).

TTL и минимальное время решения настраиваются (config.captcha_*); использованные
токены хранятся в памяти (как и rate limiting) — в пределах одного процесса.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

import config

# Время жизни задачи, сек (по умолчанию 10 минут — капчу решают сразу)
TTL_SECONDS = config.captcha_ttl_seconds
# Минимальное время решения, сек: быстрее — считаем ботом
MIN_SECONDS = config.captcha_min_seconds
# Пределы операндов (простые числа, чтобы считалось в голове)
_OPERANDS_MAX = 9
# Сколько использованных токенов держим в памяти (защита от разрастания)
_USED_SWEEP = 1000

# Числительные 0..20 для формулировки примера словами
_NUM_WORDS = (
    'ноль', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь',
    'девять', 'десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
    'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать',
    'двадцать',
)

# jti -> до какого времени (monotonic) держать как использованный
_used: dict[str, float] = {}


def _sign(payload: bytes) -> str:
    return hmac.new(
        config.secret_key.encode('utf-8'), payload, hashlib.sha256,
    ).hexdigest()


def issue() -> dict:
    """Сгенерировать задачу. Возвращает {'question': 'семь плюс три', 'token': '...'}."""
    a = secrets.randbelow(_OPERANDS_MAX) + 1
    b = secrets.randbelow(_OPERANDS_MAX) + 1
    answer = a + b
    jti = secrets.token_urlsafe(8)
    iat = int(time.time())
    exp = iat + TTL_SECONDS
    question = f'{_NUM_WORDS[a]} плюс {_NUM_WORDS[b]}'

    payload = json.dumps(
        {'ans': answer, 'iat': iat, 'exp': exp, 'jti': jti},
        separators=(',', ':'), sort_keys=True,
    ).encode('utf-8')
    token = base64.urlsafe_b64encode(payload).decode('ascii').rstrip('=') + '.' + _sign(payload)
    return {'question': question, 'token': token}


def verify(token: str | None, answer: str | None, honeypot: str | None = None) -> bool:
    """Проверить токен и ответ. Успешная проверка сжигает токен.

    honeypot — значение «ловушки» (скрытого поля формы). Человек его не видит и
    не заполняет; если непусто — это бот.
    """
    # Скрытая ловушка: заполнена — сразу отказ (не раскрываем причину наружу).
    if honeypot and str(honeypot).strip():
        return False
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

    now = int(time.time())
    if int(data.get('exp', 0)) < now:
        return False  # просрочен

    # Слишком быстрый ответ — похоже на бота (мгновенный автоответ).
    iat = int(data.get('iat', 0))
    if MIN_SECONDS > 0 and (now - iat) < MIN_SECONDS:
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
