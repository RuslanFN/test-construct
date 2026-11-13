"""Аудит-лог действий (создание/удаление тестов, управление учётками).

Пишется в отдельный файл `logs/audit.log`, не смешиваясь с техническим логом.
"""
import json
import logging
import os
from datetime import datetime, timezone

os.makedirs('logs', exist_ok=True)

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False  # не дублируем в основной лог

if not audit_logger.handlers:
    _handler = logging.FileHandler('logs/audit.log', mode='a', encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(_handler)


def audit(action: str, actor: dict | None = None, **fields) -> None:
    """Записать событие в аудит-лог.

    action — короткий код события, например 'test.deleted', 'user.blocked'.
    actor — документ пользователя (dict) или None.
    fields — произвольные доп. поля (test_id, token, ...).
    """
    entry = {
        'ts': datetime.now(timezone.utc).isoformat(),
        'action': action,
        'actor_id': str(actor['_id']) if actor else None,
        'actor_username': actor.get('username') if actor else None,
        **fields,
    }
    audit_logger.info(json.dumps(entry, ensure_ascii=False))
