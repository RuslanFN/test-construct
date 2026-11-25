import asyncio
import logging
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.mongo_client import AsyncMongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from services.env import getenv, getenv_source

log = logging.getLogger(__name__)

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    """Читаем переменную без учёта регистра (lower → UPPER → MONGO_INITDB_*)."""
    return getenv(name, default)


mongo_host = _env('mongo_host')
mongo_port = _env('mongo_port')
mongo_username = _env('mongo_username')
mongo_password = _env('mongo_password')
mongo_db_name = _env('mongo_db_name')
# База для аутентификации. Пусто — как было (пользователь в самой БД проекта).
# Для официального образа mongo root-пользователь живёт в 'admin'.
mongo_auth_source = _env('mongo_auth_source')

# Экранируем логин/пароль: спецсимволы (@ : / # ?) в пароле иначе ломают URI.
_user = quote_plus(mongo_username or '')
_pwd = quote_plus(mongo_password or '')
_auth = f'?authSource={mongo_auth_source}' if mongo_auth_source else ''
mongo_uri = f"mongodb://{_user}:{_pwd}@{mongo_host}:{mongo_port}/{mongo_db_name}{_auth}"

# Диагностика подключения (без секретов): видно, какие значения ушли в Mongo
# и из какого имени они взяты (помогает ловить дубли/опечатки в панели Amvera).
log.info(
    'Mongo: host=%s port=%s db=%s user=%s authSource=%s пароль=%s (%s симв., из %s)',
    mongo_host,
    mongo_port,
    mongo_db_name,
    mongo_username or '<пусто>',
    mongo_auth_source or '<не задан>',
    'задан' if mongo_password else 'ПУСТОЙ',
    len(mongo_password or ''),
    getenv_source('mongo_password'),
)

_client: AsyncMongoClient | None = None


def get_client() -> AsyncMongoClient:
    """Единый клиент на всё приложение (создаётся лениво)."""
    global _client
    if _client is None:
        _client = AsyncMongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            uuidRepresentation='standard',
        )
    return _client


def get_db() -> AsyncDatabase:
    return get_client()[mongo_db_name]


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


async def ensure_indexes() -> None:
    """Уникальные индексы, которые Mongo сам не создаёт."""
    await get_db()['users'].create_index('username', unique=True)
    await get_db()['users'].create_index('email', unique=True)
    await get_db()['tests'].create_index('author.user_id')
    await get_db()['tests'].create_index('public_token', unique=True, sparse=True)
    await get_db()['attempts'].create_index('test_id')
    await get_db()['attempts'].create_index('user_id')
    # по created_at работает фоновая очистка по политике хранения (retention)
    await get_db()['attempts'].create_index('created_at')
    await get_db()['media'].create_index('uploaded_by')


async def test_db() -> None:
    db = get_db()
    try:
        result = await db.command('ping')
        print(f'Успешное подключение: {result}')
    except OperationFailure as err:
        # 'Authentication failed' — соединение принято, но логин/пароль не приняты.
        print(
            f'Ошибка аутентификации Mongo: {err}. '
            f'Пользователь={mongo_username!r}, authSource={mongo_auth_source or "<не задан>"!r}, '
            f'db={mongo_db_name!r}. Проверьте, что пользователь есть в базе '
            f'{mongo_auth_source or mongo_db_name!r} и пароль совпадает.'
        )
    except ServerSelectionTimeoutError as err:
        print(f'Превышено время ожидания сервера: {err}')


if __name__ == "__main__":
    asyncio.run(test_db())

