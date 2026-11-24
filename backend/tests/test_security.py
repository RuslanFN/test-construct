"""Тесты хеширования паролей и JWT-токенов."""
import jwt

import config
import security


def test_hash_and_verify_password_roundtrip():
    h = security.hash_password('secret123')
    assert h != 'secret123'
    assert security.verify_password('secret123', h) is True
    assert security.verify_password('wrong', h) is False


def test_hash_is_salted():
    # два хеша одного пароля должны отличаться (соль)
    a = security.hash_password('same')
    b = security.hash_password('same')
    assert a != b
    assert security.verify_password('same', a)
    assert security.verify_password('same', b)


def test_access_token_roundtrip():
    token = security.create_access_token('user-123')
    assert security.decode_access_token(token) == 'user-123'


def test_refresh_token_roundtrip():
    token = security.create_refresh_token('user-456')
    assert security.decode_refresh_token(token) == 'user-456'


def test_access_token_not_accepted_as_refresh():
    token = security.create_access_token('u')
    assert security.decode_refresh_token(token) is None


def test_refresh_token_not_accepted_as_access():
    token = security.create_refresh_token('u')
    assert security.decode_access_token(token) is None


def test_tampered_token_rejected():
    token = security.create_access_token('u')
    tampered = token[:-2] + ('aa' if not token.endswith('aa') else 'bb')
    assert security.decode_access_token(tampered) is None


def test_wrong_secret_rejected():
    token = security.create_access_token('u')
    # токен, подписанный другим ключом
    payload = jwt.decode(token, config.secret_key, algorithms=[config.jwt_algorithm])
    forged = jwt.encode(payload, 'a-different-secret-key-of-sufficient-length-32', algorithm='HS256')
    assert security.decode_access_token(forged) is None


def test_expired_token_rejected(monkeypatch):
    from datetime import datetime, timedelta, timezone

    expired_payload = {
        'sub': 'u',
        'type': 'access',
        'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    token = jwt.encode(expired_payload, config.secret_key, algorithm=config.jwt_algorithm)
    assert security.decode_access_token(token) is None
