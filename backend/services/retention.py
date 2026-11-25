"""Фоновая очистка персональных данных по политике хранения (retention).

152-ФЗ: ПДн нельзя хранить дольше, чем нужно для цели. Планировщик работает
внутри процесса приложения (asyncio-задача в `lifespan`) и раз в сутки удаляет
попытки прохождения тестов старше `attempts_retention_days` (по умолчанию —
месяц, 30 дней).

Почему не отдельный cron/сервис: единый Docker-образ без compose (требование
Amvera), поэтому лишний процесс/пакет не нужен — задача живёт рядом с API.

Ограничение: при нескольких воркерах uvicorn каждая копия запустит свою задачу.
Удаление идемпотентно (повторный `delete_many` ничего не портит), но при
масштабировании планировщик лучше вынести в отдельный процесс.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import config
from db import get_db

log = logging.getLogger(__name__)


def interval_seconds() -> int:
    """Пауза между проверками, сек. По умолчанию 24 ч (раз в сутки).

    Минимум — час: опечатка в конфиге (`0`) не должна превращать очистку
    в бесконечный цикл запросов к БД.
    """
    return max(1, config.retention_check_interval_hours) * 3600


async def purge_old_attempts(now: datetime | None = None) -> int:
    """Удалить попытки старше срока хранения. Возвращает число удалённых.

    `now` параметризован для тестов; в бою берётся текущее UTC-время.
    При выключенной очистке (`attempts_retention_days <= 0`) ничего не делает.
    """
    days = config.attempts_retention_days
    if days <= 0:
        return 0
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    result = await get_db()['attempts'].delete_many({'created_at': {'$lt': cutoff}})
    deleted = result.deleted_count
    if deleted:
        log.info('Retention: удалено попыток старше %s дн.: %s', days, deleted)
    return deleted


async def retention_worker() -> None:
    """Цикл очистки: первый прогон сразу при старте, далее — раз в сутки.

    Останавливается отменой задачи в `lifespan`. Прогон при старте важен:
    контейнер может перезапускаться, и таймер паузы начинается заново.
    """
    interval = interval_seconds()
    while True:
        try:
            await purge_old_attempts()
        except asyncio.CancelledError:
            break
        except Exception as err:  # noqa: BLE001 — планировщик не должен падать от разовой ошибки
            log.warning('Retention: ошибка очистки: %s', err)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
