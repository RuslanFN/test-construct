"""Тесты аудит-логирования (факт записи JSON-строки)."""
import json
import logging

from services import audit as audit_module
from services.audit import audit


def test_audit_writes_json_line(monkeypatch):
    captured = []

    class _FakeLogger:
        def info(self, msg):
            captured.append(msg)

    monkeypatch.setattr(audit_module, 'audit_logger', _FakeLogger())

    actor = {'_id': 'user-1', 'username': 'admin'}
    audit('test.created', actor=actor, test_id='t-1', title='Мой тест')

    assert len(captured) == 1
    entry = json.loads(captured[0])
    assert entry['action'] == 'test.created'
    assert entry['actor_id'] == 'user-1'
    assert entry['actor_username'] == 'admin'
    assert entry['test_id'] == 't-1'
    assert entry['title'] == 'Мой тест'
    assert 'ts' in entry


def test_audit_without_actor(monkeypatch):
    captured = []

    class _FakeLogger:
        def info(self, msg):
            captured.append(msg)

    monkeypatch.setattr(audit_module, 'audit_logger', _FakeLogger())
    audit('system.event', foo='bar')
    entry = json.loads(captured[0])
    assert entry['actor_id'] is None
    assert entry['actor_username'] is None
    assert entry['foo'] == 'bar'
