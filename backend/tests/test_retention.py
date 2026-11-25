"""Тесты политики хранения ПДн: удаление старых попыток по `created_at`."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from services import retention


def _attempt(created_at: datetime) -> dict:
    return {
        '_id': uuid.uuid4(),
        'test_id': uuid.uuid4(),
        'score': 0,
        'total': 0,
        'percent': 0.0,
        'created_at': created_at,
    }


def test_interval_is_day_by_default(monkeypatch):
    """Проверка раз в сутки — требование политики хранения."""
    monkeypatch.setattr(retention.config, 'retention_check_interval_hours', 24)
    assert retention.interval_seconds() == 24 * 3600


def test_interval_clamped_to_one_hour(monkeypatch):
    """Опечатка/ноль в конфиге не должны давать плотный цикл запросов к БД."""
    monkeypatch.setattr(retention.config, 'retention_check_interval_hours', 0)
    assert retention.interval_seconds() == 3600


async def test_worker_purges_on_start(fake_db, monkeypatch):
    """Первый прогон — сразу при старте, не через сутки."""
    called = asyncio.Event()

    async def fake_purge(now=None) -> int:
        called.set()
        return 0

    monkeypatch.setattr(retention, 'purge_old_attempts', fake_purge)

    task = asyncio.create_task(retention.retention_worker())
    try:
        await asyncio.wait_for(called.wait(), timeout=5)
    finally:
        task.cancel()
        await task


async def test_purge_disabled_when_days_zero(fake_db, monkeypatch):
    """`0` — очистку выключили явно: данные не удаляются."""
    monkeypatch.setattr(retention.config, 'attempts_retention_days', 0)
    fake_db['attempts']._docs.append(_attempt(datetime.now(timezone.utc) - timedelta(days=1000)))
    assert await retention.purge_old_attempts() == 0
    assert len(fake_db['attempts']._docs) == 1


async def test_purge_deletes_only_expired(fake_db, monkeypatch):
    monkeypatch.setattr(retention.config, 'attempts_retention_days', 30)
    now = datetime.now(timezone.utc)
    old = _attempt(now - timedelta(days=31))
    fresh = _attempt(now - timedelta(days=1))
    fake_db['attempts']._docs.extend([old, fresh])

    deleted = await retention.purge_old_attempts(now=now)

    assert deleted == 1
    kept = fake_db['attempts']._docs
    assert len(kept) == 1
    assert kept[0]['_id'] == fresh['_id']


async def test_purge_boundary_keeps_edge(fake_db, monkeypatch):
    """Попытка ровно на границе срока (N дней) ещё не удаляется."""
    monkeypatch.setattr(retention.config, 'attempts_retention_days', 10)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    edge = _attempt(now - timedelta(days=10))
    older = _attempt(now - timedelta(days=11))
    fake_db['attempts']._docs.extend([edge, older])

    deleted = await retention.purge_old_attempts(now=now)

    assert deleted == 1
    assert len(fake_db['attempts']._docs) == 1
    assert fake_db['attempts']._docs[0]['_id'] == edge['_id']
