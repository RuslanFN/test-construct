"""Утилиты, общие для роутеров: определение IP клиента за прокси/балансировщиком."""
from fastapi import Request


def client_ip(request: Request) -> str:
    """IP клиента с учётом прокси (Amvera + наш nginx).

    Порядок доверия:
    1. X-Real-IP — наш nginx выставляет его из $remote_addr (одно значение,
       клиент его перезаписать не может, если nginx ставит его после прокси);
    2. последний адрес X-Forwarded-For — его добавил последний прокси в цепочке
       (самый надёжный среди "дописываемых" вариантов);
    3. адрес сокета.

    ВАЖНО: НЕ берём первый адрес XFF — его контролирует клиент (подделка).
    """
    real_ip = request.headers.get('x-real-ip')
    if real_ip:
        return real_ip.strip()

    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        # Правый адрес добавляет наш доверенный прокси, левые — клиент.
        return forwarded.split(',')[-1].strip()

    return request.client.host if request.client else 'unknown'
