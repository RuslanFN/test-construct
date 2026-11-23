"""Диагностика окружения запроса (только администратор).

Нужен, чтобы на проде понять, какие заголовки доходят до backend за
балансировщиком/прокси (Amvera): реальный адрес сокета, X-Forwarded-For,
X-Real-IP. Наружу без авторизации не отдаётся.
"""
from fastapi import APIRouter, Depends, Request

import config
from services.deps import require_admin

router = APIRouter(prefix='/api/debug', tags=['debug'],
                   dependencies=[Depends(require_admin)])


@router.get('/ip')
async def debug_ip(request: Request, current=Depends(require_admin)):
    """Эхо того, что реально пришло на backend.

    Пример проверки подделки:
        curl.exe -s -b cookies.txt "<host>/api/debug/ip" -H "X-Forwarded-For: 9.9.9.9"
    Если подставленный 9.9.9.9 сохранился в x_forwarded_for — заголовок
    клиента не отбрасывается (см. docs/architecture.md, раздел про IP за прокси).
    """
    return {
        'remote_addr': request.client.host if request.client else None,
        'x_forwarded_for': request.headers.get('x-forwarded-for'),
        'x_real_ip': request.headers.get('x-real-ip'),
        'x_forwarded_proto': request.headers.get('x-forwarded-proto'),
        'host': request.headers.get('host'),
        'user_agent': request.headers.get('user-agent'),
        'cookie_secure': config.cookie_secure,
    }
