"""Утилиты, общие для роутеров: определение IP клиента за прокси/балансировщиком."""
from fastapi import Request

import config


def client_ip(request: Request) -> str:
    """IP клиента.

    Источник задаётся `config.trusted_client_ip_header`:
      - 'x-envoy-external-address' — Amvera/Envoy (перезаписывает клиентский);
      - 'x-real-ip'                — свой nginx с real_ip ($remote_addr);
      - 'x-forwarded-for'          — берём ПОСЛЕДНИЙ адрес (добавил последний прокси);
      - '' (пусто)                 — не доверяем заголовкам, адрес сокета.

    Значение заголовка валидно ТОЛЬКО если его ставит доверенный прокси и
    перезаписывает клиентский вариант. Для прямого доступа — пустая настройка.
    """
    header_name = (config.trusted_client_ip_header or '').strip().lower()
    if header_name:
        value = request.headers.get(header_name)
        if value:
            if header_name == 'x-forwarded-for':
                return value.split(',')[-1].strip()
            return value.strip()

    return request.client.host if request.client else 'unknown'

