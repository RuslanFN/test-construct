# Тесты бэкенда

Полный набор тестов на весь функционал API, сервисов, схем и утилит.
Тесты **не требуют MongoDB и сети**: используется in-memory эмулятор
async-коллекций pymongo (`tests/fakedb.py`), а медиа пишутся во временный
каталог.

## Запуск

```bash
cd backend

# один раз: тестовые зависимости
pip install -r requirements-dev.txt

# весь набор
python -m pytest

# смотреть, какие тесты выполняются
python -m pytest -v

# отдельный файл / тест
python -m pytest tests/test_auth_router.py
python -m pytest tests/test_attempt_service.py::test_submit_one_correct
```

> Переменные окружения (JWT_SECRET, ADMIN_PASSWORD, MONGO_*) для тестов
> выставляются автоматически в `tests/conftest.py` — настраивать ничего не нужно.

## Структура

| Файл | Что покрывает |
|------|---------------|
| `fakedb.py` | In-memory async-эмулятор коллекций pymongo (инфраструктура) |
| `conftest.py` | Env, патч `get_db`, фикстуры (`api_client`, `fake_db`, ...) |
| `test_health.py` | Приложение поднимается, `/api/health`, lifespan создаёт админа |
| `test_security.py` | bcrypt-хеши, `stub_hash` (bcrypt всегда сверяется), JWT access/refresh, типы токенов, подпись, истечение |
| `test_env.py` | Чтение env без учёта регистра, кавычки, алиасы |
| `test_ratelimit.py` | Лимит попыток входа, блокировка, сброс, изоляция ключей |
| `test_schemas_user.py` | Валидация регистрации (логин/почта/пароль/ФИО/согласие) |
| `test_schemas_attempt.py` | Валидация участника и ответов (сертификат, ФИО) |
| `test_permissions.py` | Проверки ролей (`is_admin`, `is_service`) |
| `test_user_service.py` | Создание/аутентификация/удаление пользователя, `user_to_public` |
| `test_deps.py` | `get_current_user` (cookie/Bearer), `require_admin` |
| `test_test_service.py` | CRUD тестов, оптимистичная блокировка, публикация, права, to_public/to_detail |
| `test_attempt_service.py` | Проверка ответов all типов, обязательные, подсчёт, детали, Excel |
| `test_admin_service.py` | Поиск тестов, управление учётками, защита служебной учётки |
| `test_media_service.py` | Детект формата, лимиты, path traversal, сохранение/удаление, права |
| `test_image_bomb.py` | Бомба декомпрессии (лимит `MAX_PIXELS`), анонимная загрузка |
| `test_seed.py` | Создание/синхронизация администратора |
| `test_audit.py` | Запись аудит-событий в JSON |
| `test_auth_router.py` | `/api/auth/*`: register, login, refresh, logout, me, delete |
| `test_tests_router.py` | `/api/tests/*`: CRUD, publish, attempts, export, detail |
| `test_public_router.py` | `/api/public/*`: тест по токену, прохождение |
| `test_admin_router.py` | `/api/admin/*`: доступ, пользователи, тесты |
| `test_media_router.py` | `/api/media/*`: загрузка, отдача, удаление, лимиты |

## Подход

- Для async-тестов не нужен `pytest-asyncio`: в `conftest.py` есть хук
  `pytest_pyfunc_call`, который запускает `async def test_*` через `asyncio.run`.
- Фикстура `client` намеренно названа `api_client` — чтобы не конфликтовать
  с плагином `pytest-flask`, если он установлен в окружении.
