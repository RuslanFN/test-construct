"""Диагностика окружения запроса (только администратор).

Нужен, чтобы на проде понять, какие заголовки доходят до backend за
балансировщиком/прокси (Amvera): реальный адрес сокета, X-Forwarded-For,
X-Real-IP. Наружу без авторизации не отдаётся.
"""
from fastapi import APIRouter, Depends, Request

import config
from services.deps import require_admin
from services.http_client import client_ip

router = APIRouter(prefix='/api/debug', tags=['debug'],
                   dependencies=[Depends(require_admin)])


@router.get('/ip')
async def debug_ip(request: Request, current=Depends(require_admin)):
    """Эхо того, что реально пришло на backend.

    Пример проверки подделки:
        curl.exe -s -b cookies.txt "<host>/api/debug/ip" -H "X-Forwarded-For: 9.9.9.9"
    Если подставленный 9.9.9.9 сохранился в x_forwarded_for — заголовок
    клиента не отбрасывается (см. docs/architecture.md, раздел про IP за прокси).

    Возвращаем ВСЕ заголовки как есть: за балансировщиком Amvera реальный IP
    клиента может лежать в нестандартном заголовке. Заодно показываем, что
    вернёт client_ip() для текущего запроса.
    """
    xff = request.headers.get('x-forwarded-for')
    xff_parts = [p.strip() for p in xff.split(',')] if xff else []
    return {
        'remote_addr': request.client.host if request.client else None,
        'x_forwarded_for': xff,
        'xff_first': xff_parts[0] if xff_parts else None,
        'xff_last': xff_parts[-1] if xff_parts else None,
        'x_real_ip': request.headers.get('x-real-ip'),
        'x_forwarded_proto': request.headers.get('x-forwarded-proto'),
        'client_ip_resolved': client_ip(request),
        'cookie_secure': config.cookie_secure,
        'headers': dict(request.headers),
    }
