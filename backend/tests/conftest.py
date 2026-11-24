"""Общая конфигурация pytest: окружение, фейковая БД, клиент и фикстуры.

Важно: переменные окружения выставляются ДО импорта приложения, потому что
config.py при импорте проверяет jwt_secret/admin_password и падает иначе.
"""
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

# --- env до импорта config/db/main ---
os.environ.setdefault('JWT_SECRET', 'test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz')
os.environ.setdefault('ADMIN_PASSWORD', 'test-admin-pass-123')
os.environ.setdefault('MONGO_HOST', 'localhost')
os.environ.setdefault('MONGO_PORT', '27017')
os.environ.setdefault('MONGO_DB_NAME', 'testdb')
os.environ.setdefault('MONGO_USERNAME', 'u')
os.environ.setdefault('MONGO_PASSWORD', 'p')
os.environ.setdefault('COOKIE_SECURE', 'false')
os.environ.setdefault('PD_CONSENT_VERSION', '1.0')

# backend/ в sys.path, чтобы импорты вида "import config", "from services..." работали
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest  # noqa: E402

from tests.fakedb import FakeDatabase  # noqa: E402


def pytest_pyfunc_call(pyfuncitem):
    """Позволяет писать async def test_* без pytest-asyncio.

    Если тест-функция — корутина, запускаем её через asyncio.run.
    """
    import asyncio
    import inspect

    test_func = pyfuncitem.obj
    if inspect.iscoroutinefunction(test_func):
        sig = inspect.signature(test_func)
        kwargs = {
            name: pyfuncitem.funcargs[name]
            for name in sig.parameters
            if name in pyfuncitem.funcargs and name not in ('request', 'event_loop')
        }
        asyncio.run(test_func(**kwargs))
        return True
    return None


def _patch_all_get_db(fake: FakeDatabase) -> None:
    """Заменяет функцию get_db во всех импортированных модулях приложения.

    Модули делают `from db import get_db`, поэтому держат собственную ссылку
    на функцию. Патчим ссылку в каждом модуле, где она встречается.
    """
    import db as db_module

    fake_get_db = lambda: fake  # noqa: E731
    db_module.get_db = fake_get_db

    for mod_name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        if getattr(mod, '__name__', '').startswith('tests'):
            continue
        if hasattr(mod, 'get_db'):
            try:
                setattr(mod, 'get_db', fake_get_db)
            except (AttributeError, TypeError):
                pass


@pytest.fixture()
def fake_db(monkeypatch, tmp_path):
    """Свежая in-memory БД и временный каталог для медиа на каждый тест."""
    fake = FakeDatabase()
    _patch_all_get_db(fake)
    # медиа пишем во временный каталог теста
    monkeypatch.setenv('media_dir', str(tmp_path / 'uploads'))
    monkeypatch.setenv('MEDIA_DIR', str(tmp_path / 'uploads'))
    yield fake
    fake.reset()


@pytest.fixture()
def fastapi_app(fake_db):
    """Приложение FastAPI без запуска lifespan (без подключения к Mongo)."""
    import main

    return main.app


@pytest.fixture(autouse=True)
def captcha_no_min_delay(monkeypatch):
    """Интеграционные тесты получают капчу и отправляют ответ сразу.

    Порог «слишком быстро» (по умолчанию 1 сек) в тестах отключаем — иначе
    любой валидный сценарий был бы отклонён как бот. Сама проверка порога
    покрыта отдельными тестами в test_captcha_ratelimit.py.
    """
    from services import captcha

    monkeypatch.setattr(captcha, 'MIN_SECONDS', 0.0)


@pytest.fixture()
def api_client(fastapi_app):
    from fastapi.testclient import TestClient

    # не поднимаем lifespan: поднимать Mongo не нужно, БД уже подменена
    with TestClient(fastapi_app) as c:
        yield c


# ---- хелперы для создания сущностей напрямую в fake_db ----


def make_user_doc(
    *,
    username: str = 'metodist',
    email: str | None = None,
    password: str = 'password123',
    role: str = 'metodist',
    is_active: bool = True,
    approval_status: str = 'approved',
    is_service: bool = False,
    first_name: str = 'Иван',
    last_name: str = 'Иванов',
    user_id: uuid.UUID | None = None,
) -> dict:
    from security import hash_password

    uid = user_id or uuid.uuid4()
    return {
        '_id': uid,
        'username': username,
        'email': email or f'{username}@example.com',
        'phone': None,
        'first_name': first_name,
        'last_name': last_name,
        'middle_name': None,
        'role': role,
        'hashed_password': hash_password(password),
        'is_active': is_active,
        'is_service': is_service,
        'approval_status': approval_status,
        'approved_at': datetime.now(timezone.utc) if approval_status == 'approved' else None,
        'pd_consent': {'granted': True, 'granted_at': datetime.now(timezone.utc), 'version': '1.0'},
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }


@pytest.fixture()
def admin_doc(fake_db):
    doc = make_user_doc(username='admin', role='admin', is_service=True)
    fake_db['users']._docs.append(doc)
    return doc


@pytest.fixture()
def metodist_doc(fake_db):
    doc = make_user_doc(username='metodist')
    fake_db['users']._docs.append(doc)
    return doc


@pytest.fixture()
def auth_headers():
    """Фабрика заголовков Authorization: Bearer для пользователя."""
    from security import create_access_token

    def _make(user_doc: dict) -> dict:
        token = create_access_token(str(user_doc['_id']))
        return {'Authorization': f'Bearer {token}'}

    return _make


def make_question(
    qtype: str = 'one',
    *,
    text: str = 'Вопрос?',
    required: bool = False,
    answers: list | None = None,
    pairs: list | None = None,
    image_ids: list | None = None,
    qid: uuid.UUID | None = None,
) -> dict:
    """Собирает dict вопроса (как в документе теста)."""
    answers = answers if answers is not None else [
        {'id': str(uuid.uuid4()), 'text': 'Верно', 'is_correct': True},
        {'id': str(uuid.uuid4()), 'text': 'Неверно', 'is_correct': False},
    ]
    pairs = pairs if pairs is not None else []
    return {
        'id': str(qid or uuid.uuid4()),
        'type': qtype,
        'text': text,
        'required': required,
        'answers': answers,
        'pairs': pairs,
        'image_ids': [str(i) for i in (image_ids or [])],
        'order': 0,
    }


def make_test_doc(
    *,
    author_id: uuid.UUID,
    author_username: str = 'metodist',
    title: str = 'Тест',
    status: str = 'draft',
    questions: list | None = None,
    public_token: str = 'tok123',
    test_id: uuid.UUID | None = None,
) -> dict:
    return {
        '_id': test_id or uuid.uuid4(),
        'title': title,
        'description': None,
        'author': {'user_id': author_id, 'username': author_username},
        'status': status,
        'public_token': public_token,
        'questions': questions or [],
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
