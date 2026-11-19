"""Тесты чтения переменных окружения (getenv с нормализацией)."""
from services.env import getenv


def test_getenv_lowercase(monkeypatch):
    monkeypatch.setenv('my_var', 'value')
    assert getenv('my_var') == 'value'


def test_getenv_uppercase(monkeypatch):
    monkeypatch.delenv('my_var', raising=False)
    monkeypatch.setenv('MY_VAR', 'upper')
    assert getenv('my_var') == 'upper'


def test_getenv_default(monkeypatch):
    monkeypatch.delenv('missing_var', raising=False)
    monkeypatch.delenv('MISSING_VAR', raising=False)
    assert getenv('missing_var', 'dflt') == 'dflt'


def test_getenv_strips_quotes(monkeypatch):
    monkeypatch.setenv('quoted_var', '"value"')
    assert getenv('quoted_var') == 'value'
    monkeypatch.setenv('single_var', "'value'")
    assert getenv('single_var') == 'value'


def test_getenv_strips_whitespace(monkeypatch):
    monkeypatch.setenv('space_var', '  value  ')
    assert getenv('space_var') == 'value'


def test_getenv_alias(monkeypatch):
    # mongo_username подхватывается из MONGO_INITDB_ROOT_USERNAME
    monkeypatch.delenv('mongo_username', raising=False)
    monkeypatch.delenv('MONGO_USERNAME', raising=False)
    monkeypatch.setenv('MONGO_INITDB_ROOT_USERNAME', 'rootuser')
    assert getenv('mongo_username') == 'rootuser'
