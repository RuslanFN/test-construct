"""Чтение переменных окружения с нормализацией имён.

Amvera хранит переменные только в ВЕРХНЕМ регистре (JWT_SECRET,
ADMIN_PASSWORD, ...), а в коде и локальном .env имена заданы в нижнем
(jwt_secret, ...). Хелпер приводит имя к нижнему регистру и ищет переменную
без учёта регистра. Значение очищается от обрамляющих кавычек и пробелов
(частая ошибка в .env).
"""
import os


# Альтернативные (устаревшие/стандартные) имена: основное имя -> набор синонимов.
# Удобно, когда на сервере переменные уже заведены под именами официального
# образа Mongo (MONGO_INITDB_ROOT_USERNAME и т.п.).
_ALIASES: dict[str, tuple[str, ...]] = {
    'mongo_username': ('MONGO_INITDB_ROOT_USERNAME',),
    'mongo_password': ('MONGO_INITDB_ROOT_PASSWORD',),
    'mongo_db_name': ('MONGO_INITDB_DATABASE',),
}


def getenv(name: str, default: str | None = None) -> str | None:
    """Найти переменную регистронезависимо.

    Имя нормализуется к нижнему регистру; поиск идёт по нижнему варианту,
    затем по UPPER, затем — по известным синонимам (см. _ALIASES).
    Значение очищается от обрамляющих кавычек и пробелов.
    """
    val = os.getenv(name.lower())
    if val is None:
        val = os.getenv(name.upper())
    if val is None:
        for alias in _ALIASES.get(name.lower(), ()):
            val = os.getenv(alias)
            if val is not None:
                break
    if val is None:
        return default
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        val = val[1:-1]
    return val


def getenv_source(name: str) -> str:
    """Имя переменной, из которого реально взято значение (для диагностики).

    Возвращает 'lower:<имя>', 'upper:<имя>', 'alias:<имя>' или '<нет>'.
    Полезно в логах: сразу видно, подхватилось ли нужное имя.
    """
    candidates = [(name.lower(), 'lower'), (name.upper(), 'upper')]
    candidates += [(a, 'alias') for a in _ALIASES.get(name.lower(), ())]
    for key, kind in candidates:
        if os.getenv(key) is not None:
            return f'{kind}:{key}'
    return '<нет>'
