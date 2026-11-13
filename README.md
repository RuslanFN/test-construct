ь # Платформа онлайн-тестирования

Сервис для проведения тестирования обучающихся методистами сети технопарков «Кванториум».

## Стек

- **Backend:** FastAPI + uvicorn, PyMongo (Async), JWT в HttpOnly-cookie.
- **Frontend:** Vue 3 + Vite, раздаётся через nginx.
- **БД:** MongoDB 7.
- **Развёртывание:** Docker Compose (backend + mongo + nginx-фронт в одном файле).

## Быстрый запуск (Docker)

```bash
# 1. Подготовить переменные окружения
cp env.example .env
# отредактировать .env: задать MONGO_PASSWORD, jwt_secret, admin_password

# 2. Сгенерировать надёжный jwt_secret:
python -c "import secrets;print(secrets.token_urlsafe(48))"

# 3. Поднять весь стек
docker compose up -d --build
```

Сайт: `http://<host>:80` (порт задаётся `WEB_PORT` в `.env`).
API healthcheck: `http://<host>/api/health`.

### Структура сервисов

| Сервис    | Описание                                              | Порт наружу |
|-----------|-------------------------------------------------------|-------------|
| `web`     | nginx: статика фронта + проксирование `/api`          | `WEB_PORT`  |
| `backend` | FastAPI (uvicorn), доступен только внутри сети compose | —           |
| `mongo`   | MongoDB 7 с volume `mongo_data`                        | —           |

Порт базы и backend **наружу не публикуются** — доступ только через `web`/внутреннюю сеть.

## Деплой на Amvera (один Dockerfile)

Amvera **не поддерживает** `docker-compose`. Проект собирается в **единый образ**
(корневой `Dockerfile`): Vite собирает фронт → nginx отдаёт статику и проксирует
`/api` на uvicorn, запущенный в том же контейнере (`docker/start.sh`).

- `amvera.yml` — манифест (`environment: docker`, `containerPort: 80`).
- **MongoDB выносится отдельно**: managed-MongoDB Amvera или внешний сервер.
  Хост/порт/логин/пароль задаются переменными в панели Amvera:
  `mongo_host`, `mongo_port`, `mongo_username`, `mongo_password`, `mongo_db_name`,
  при необходимости `mongo_auth_source`.
- Публичный порт контейнера — **80**.

### Переменные в панели Amvera (→ «Переменные»)

Обязательные (секреты — с галочкой «Секрет»):

```
mongo_host=<хост Mongo>
mongo_port=27017
mongo_username=<логин>
mongo_password=<пароль>          # Секрет
mongo_db_name=tests
jwt_secret=<случайная строка >=32>   # Секрет
admin_username=admin
admin_email=<email>
admin_password=<сильный пароль>      # Секрет
cookie_secure=true
cookie_samesite=strict
log_level=INFO
```

> На Amvera за HTTPS обязательно `cookie_secure=true`.

### Деплой через git

```bash
git remote add amvera <url-репозитория-Amvera>
git push amvera main
```

## Переменные окружения

Основные (см. `env.example`):

- `MONGO_USERNAME`, `MONGO_PASSWORD`, `MONGO_DB_NAME` — доступ к MongoDB.
- `jwt_secret` — секрет подписи JWT (≥ 32 символов, обязательно случайный).
- `admin_username`, `admin_email`, `admin_password` — учётка администратора (создаётся при первом старте).
- `cookie_secure` — `true` в проде за HTTPS, `false` для http-теста.
- `WEB_PORT` — внешний порт сайта.

## Разработка (без Docker)

Backend:
```bash
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8081
```

Frontend:
```bash
cd frontend/online_test
npm install
npm run dev      # http://localhost:5173, /api проксируется на :8081
```

## Резервное копирование БД

```bash
docker compose exec mongo mongodump --username "$MONGO_USERNAME" --password "$MONGO_PASSWORD" \
  --authenticationDatabase admin --db tests --archive=/tmp/backup.gz --gzip
docker compose cp mongo:/tmp/backup.gz ./backup-$(date +%F).gz
```

## Безопасность (кратко)

- Пароли хранятся в виде bcrypt-хэшей.
- JWT — в HttpOnly-cookie (недоступны JS), refresh-токен с ротацией.
- Учётные записи методистов требуют подтверждения администратором.
- Порт БД и backend не публикуются наружу.

Подробный аудит безопасности и соответствие 152-ФЗ — см. `docs/security-audit.md`.
