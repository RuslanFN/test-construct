# Архитектура проекта «Платформа онлайн-тестирования»

> Документ для продолжения работы в новых диалогах: что за проект, как устроен,
> какие решения приняты и почему. При расхождении с кодом — **истина в коде**,
> тогда обновите этот файл.

---

## 1. Суть проекта и идея

**Что это.** Веб-сервис для проведения онлайн-тестирования обучающихся сети
детских технопарков «Кванториум». Методист создаёт тест в визуальном конструкторе,
публикует его и передаёт ссылку участникам. Участник проходит тест **без регистрации**:
вводит ФИО и номер сертификата ПФДО, отвечает на вопросы и сразу видит результат.
Методист видит все попытки, разбор по вопросам и выгружает их в Excel.

**Ключевая идея — две разные аудитории:**

| Роль | Аккаунт | Что делает |
|---|---|---|
| **Методист** | да (логин/пароль, подтверждение админом) | создаёт, редактирует, публикует тесты; смотрит результаты и выгрузки |
| **Администратор** | да (служебная учётка из `.env`) | подтверждает/блокирует методистов, видит все тесты |
| **Участник** | **нет** | проходит тест по публичной ссылке, получает % правильных |

Публичность участника — осознанное решение: дети и педагоги не должны регистрироваться,
чтобы пройти тест. Идентификация — по ФИО + номеру сертификата, которые вводит сам участник.

**Доменная модель в одном предложении:** методист создаёт `Test` с встроенными
`Question` (4 типа), публикует → получает `public_token` → участник проходит по ссылке →
создаётся `Attempt` со снимком ответов и результатом.

---

## 2. Технологический стек

| Слой | Технологии |
|---|---|
| **Backend** | Python 3.12, FastAPI, uvicorn, Pydantic v2 |
| **БД** | MongoDB 7, драйвер `pymongo` (async, `AsyncMongoClient`) |
| **Аутентификация** | JWT (PyJWT, HS256) в HttpOnly-cookie, bcrypt через `passlib` |
| **Frontend** | Vue 3 (`<script setup>`), Vue Router (hash history), Vite |
| **Раздача** | nginx: статика + прокси `/api` на uvicorn |
| **Изображения** | файлы на диске (`/data/uploads`), метаданные в Mongo, Pillow для валидации |
| **Excel** | openpyxl |
| **Деплой** | Docker, **единый образ** (frontend + backend + nginx), Amvera |
| **Версионирование** | git; удалённые `origin` и `amvera` |

**Порты:** наружу 80 (`containerPort` в `amvera.yml`); внутри контейнера uvicorn на `127.0.0.1:8081`.

---

## 3. Структура репозитория

```
online_test/
├── Dockerfile              # ЕДИНЫЙ образ: build фронта → nginx + uvicorn
├── amvera.yml              # манифест Amvera (environment: docker, containerPort: 80)
├── docker-compose.yml      # для локальной разработки (НЕ используется на Amvera)
├── docker/
│   ├── nginx.conf          # статика + прокси /api/ → 127.0.0.1:8081
│   └── start.sh            # запуск uvicorn в фоне + nginx на переднем плане
├── docs/
│   ├── architecture.md     # ← этот файл
│   └── security-audit.md   # аудит безопасности и 152-ФЗ
├── backend/
│   ├── main.py             # FastAPI app, роутеры, обработчик 422 на русском
│   ├── config.py           # настройки из env (валидирует jwt_secret, admin_password)
│   ├── db.py               # async Mongo-клиент, ensure_indexes()
│   ├── security.py         # bcrypt, JWT (access/refresh с type-claim)
│   ├── seed.py             # создание/синхронизация служебного админа при старте
│   ├── models/             # документы Mongo (Pydantic)
│   ├── schemas/            # контракты API (запрос/ответ)
│   ├── routers/            # эндпоинты по доменам
│   ├── services/           # бизнес-логика
│   ├── controllers/        # (пусто, задел)
│   └── requirements.txt
└── frontend/online_test/
    ├── vite.config.js      # dev-прокси /api → 127.0.0.1:8081
    └── src/
        ├── main.js, App.vue, router.js, api.js, auth.js
        ├── components/     # AppHeader.vue, ImageCarousel.vue (+ carousel.css)
        ├── user/           # Login.vue, UserProfile.vue, Results.vue
        ├── constructor/    # Constructor.vue + редакторы по типам + ImageUpload.vue
        ├── public/         # TakeTest.vue (прохождение по ссылке)
        └── admin/          # Admin.vue
```

---

## 4. Слоистый backend

Направление зависимостей строгое, снизу вверх:

```
routers  →  services  →  models/db
   ↓
schemas (контракты API, едины для всех слоёв)
```

| Слой | Ответственность | Чего не делает |
|---|---|---|
| `routers/` | HTTP: пути, коды, зависимости, `response_model` | бизнес-логику |
| `services/` | бизнес-логика, проверки прав, работа с Mongo | работу с `Request`/`Response` |
| `models/` | Pydantic-модели документов Mongo (`id` → `_id`) | валидацию ввода пользователя |
| `schemas/` | что приходит и уходит по HTTP | хранение |
| `db.py` | клиент Mongo, индексы | доменную логику |
| `config.py` | чтение env, дефолты, падение при небезопасных настройках | — |

**Разделение model/schema — важное правило.** `User` (model) содержит `hashed_password`
и никогда не отдаётся наружу; `UserPublic` (schema) — то, что уходит клиенту, без хэша.
Не смешивать.

### Роутеры

| Префикс | Файл | Назначение |
|---|---|---|
| `/api/auth` | `routers/auth.py` | регистрация, логин, refresh, logout, me, удаление аккаунта |
| `/api/tests` | `routers/tests.py` | CRUD тестов, публикация, попытки, экспорт |
| `/api/public` | `routers/public.py` | **без авторизации**: получить тест по токену, отправить ответы |
| `/api/admin` | `routers/admin.py` | поиск тестов, управление учётками (только admin) |
| `/api/media` | `routers/media_router.py` | загрузка/отдача/удаление изображений |
| `/api/health` | `main.py` | healthcheck |

---

## 5. Модель данных (MongoDB)

Четыре коллекции. Агрегаты (тест с вопросами) хранятся **встроенно** — тест всегда
редактируется и читается целиком, отдельная коллекция вопросов не нужна.

### `users`

```python
{
  '_id': UUID, 'username': str (uniq), 'email': str (uniq),
  'phone': str|None,
  'first_name': str, 'last_name': str, 'middle_name': str|None,
  'role': 'admin' | 'metodist',
  'hashed_password': str,          # bcrypt, наружу НЕ отдаётся
  'is_active': bool,
  'is_service': bool,              # служебный админ: нельзя удалить/заблокировать
  'approval_status': 'pending' | 'approved' | 'rejected',
  'approved_at': datetime|None,
  'pd_consent': {'granted': bool, 'granted_at': datetime, 'version': str},
  'created_at': datetime, 'updated_at': datetime,
}
```

### `tests`

```python
{
  '_id': UUID,
  'title': str, 'description': str|None,
  'author': {'user_id': UUID, 'username': str},   # ДЕНОРМАЛИЗОВАННЫЙ снимок
  'status': 'draft' | 'published',
  'public_token': str (uniq),                     # ссылка /take/<token>
  'questions': [                                  # ВСТРОЕННЫЙ массив
    {
      'id': UUID, 'type': 'one'|'some'|'match'|'text',
      'text': str, 'required': bool,
      'answers': [{'id': UUID, 'text': str, 'is_correct': bool}],  # one/some/text
      'pairs':   [{'id': UUID, 'left': str, 'right': str}],        # match
      'image_ids': [UUID],                        # ссылки в коллекцию media
      'order': int,
      'created_at': datetime, 'updated_at': datetime,
    },
  ],
  'created_at': datetime, 'updated_at': datetime,
}
```

**Почему `author` денормализован:** список тестов показывает имя автора без join
к `users`. Источник правды — `users`, здесь снимок на момент сохранения.

### `attempts`

```python
{
  '_id': UUID, 'test_id': UUID, 'test_title': str,   # title — снимок
  'user_id': UUID|None,                              # для аналитики, обычно None
  'guest_name': str|None,                            # legacy
  'participant': {                                   # ПДн участника
    'last_name': str, 'first_name': str,
    'middle_name': str|None, 'certificate_number': str,   # 10 цифр
  },
  'score': int, 'total': int, 'percent': float,
  'results': [
    {
      'question_id': UUID, 'is_correct': bool,
      # СНИМОК на момент прохождения:
      'text': str,
      'given_texts': [str], 'correct_texts': [str],
      # legacy id-ссылки (для старых попыток):
      'given_answer': [str], 'correct_answer': [str],
    },
  ],
  'created_at': datetime,
}
```

**Снимок в `QuestionResult` — принципиальное решение.** Попытка хранит тексты вопроса
и ответов на момент прохождения. Поэтому правка/удаление вариантов в тесте **не искажает**
уже сохранённые результаты. Старые попытки (без снимка) читаются по id через fallback.

### `media`

```python
{
  '_id': UUID,
  'filename': str,          # оригинальное имя (только для отображения)
  'stored_name': str,       # <uuid4.hex><ext> — реальное имя файла на диске
  'content_type': 'image/png'|'image/jpeg'|'image/webp',
  'size': int, 'width': int|None, 'height': int|None,
  'uploaded_by': UUID,
  'created_at': datetime,
}
```

**Связи:** `tests.questions[].image_ids` → `media._id` → `media.stored_name` → файл на диске.

### Индексы (`db.ensure_indexes`)

`users.username` (uniq), `users.email` (uniq), `tests.author.user_id`,
`tests.public_token` (uniq, sparse), `attempts.test_id`, `attempts.user_id`,
`media.uploaded_by`.

---

## 6. Типы вопросов

Значения enum совпадают на бэкенде (`models/question_type.py`) и фронте
(`constructor/schemas.ts`) — меняются только синхронно.

| `type` | Поле с контентом | Проверка |
|---|---|---|
| `one` | `answers`, у одного `is_correct: true` | множество выбранных == множество правильных |
| `some` | `answers`, несколько `is_correct` | строгое равенство множеств (лишний выбранный = неверно) |
| `text` | `answers[0].text` — эталон | сравнение без учёта регистра и пробелов по краям |
| `match` | `pairs` (left/right) | участник расставляет правые варианты по позициям; сверяются все пары |

**Особенность `match`:** позиция правого варианта кодируется индексом, ответ хранится как
`"<leftIdx>:<rightText>"`. Поэтому при изменении порядка пар в тесте старые попытки
читаются **из снимка**, а не пересчётом индексов.

---

## 7. Жизненный цикл теста (статусы, а не версии)

```
      создание
         ↓
    ┌─────────┐   publish    ┌───────────┐
    │  draft  │ ───────────► │ published │
    └─────────┘ ◄─────────── └───────────┘
         ▲      unpublish           │
         │                          │ прохождение по /take/<token>
    редактирование            попытки (attempts)
```

**Правила, зафиксированные в коде:**

1. **Опубликованный тест нельзя редактировать.** `update_test` → **409**:
   «Опубликованный тест нельзя редактировать. Снимите его с публикации…»
   На фронте: `fieldset disabled`, серые кнопки, баннер; в профиле кнопка «Редактировать» `disabled`.
2. **Редактировать можно только черновик** — после снятия с публикации.
3. **`public_token` не меняется** при переопубликации: та же ссылка снова активна.
4. **Прохождение только по текущей версии.** `get_published_by_token` фильтрует
   `status: 'published'`; если тест сняли — **404** «Тест снят с публикации или был удалён».
   Фронт показывает это сообщение и не сохраняет результат.
5. **Защита от конкурентного редактирования:** клиент присылает `expected_updated_at`;
   если на сервере `updated_at` новее — **409** «Тест был изменён в другом окне».

### Версионности НЕТ — это осознанно

Отдельной сущности «версия теста» нет: нет номеров версий, истории, откатов,
привязки попытки к версии. Защиту от последствий правок дают:

- запрет редактирования опубликованного;
- **снимок текстов в попытке** (`QuestionResult.text / given_texts / correct_texts`).

Решение принято пользователем: «версионность не нужна, опубликованный тест не проходят».
Если понадобится «какая редакция» — минимальный вариант: `version: int` в тесте +
`test_version` в попытке (~30 строк).

---

## 8. Аутентификация и авторизация

**JWT в HttpOnly-cookie.** В JS токен недоступен (защита от XSS-кражи).

| Кука | Назначение | Время жизни |
|---|---|---|
| `access_token` | доступ к API | `jwt_expire_minutes` (60) |
| `refresh_token` | продление сессии | `refresh_token_expire_days` (14) |

- Токены различаются claim `type` (`access`/`refresh`) — один нельзя использовать как другой.
- **Ротация:** `/api/auth/refresh` выдаёт новую пару.
- `cookie_secure=true` обязательна на проде (HTTPS); `cookie_samesite=strict` (CSRF).
- **Запасной путь:** `Authorization: Bearer` поддерживается для API-клиентов/тестов,
  приоритет — у cookie.
- **Регистрация:** публичный пользователь всегда `metodist`, `is_active=false`,
  `approval_status=pending`. Вход запрещён до подтверждения админом.
- **Rate limiting:** `services/ratelimit.py`, in-memory, ключ `IP|username`,
  5 неудач за 5 минут → блокировка на 5 минут (HTTP 429 + `Retry-After`).
  ⚠️ In-memory, работает в пределах одного процесса (для нескольких воркеров нужен Redis).
- **Служебный админ** (`is_service`) создаётся из `.env` при старте (`seed.py`),
  пароль синхронизируется с `.env`; его нельзя удалить/заблокировать.
- **Удаление аккаунта** (`DELETE /api/auth/me`) обезличивает связанные попытки.

**Зависимости FastAPI:** `get_current_user` (любая роль), `require_admin` (только админ).

---

## 9. API: сводка эндпоинтов

### Публичные (без токена)
| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/public/tests/{token}` | тест для прохождения (без правильных ответов) |
| POST | `/api/public/tests/{token}/submit` | принять ответы, вернуть результат |
| GET | `/api/media/{id}` | отдать изображение (`Cache-Control: immutable`, `nosniff`) |
| POST | `/api/auth/login`, `/register`, `/refresh`, `/logout` | аутентификация |

### Методист (авторизация)
| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/tests` | мои тесты |
| POST | `/api/tests` | создать тест |
| GET / PUT / DELETE | `/api/tests/{id}` | получить (для конструктора) / изменить / удалить |
| POST | `/api/tests/{id}/publish`, `/unpublish` | публикация / снятие |
| GET | `/api/tests/{id}/attempts` | попытки + сводка (средний %) |
| GET | `/api/tests/{id}/attempts/{aid}` | разбор одной попытки |
| GET | `/api/tests/{id}/attempts/export` | выгрузка в `.xlsx` |
| POST | `/api/media` | загрузить изображение |
| DELETE | `/api/media/{id}` | удалить изображение (владелец/админ) |

### Администратор
| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/admin/tests` | все тесты (поиск по названию/токену/uuid, статус, автор) |
| GET | `/api/admin/users` | все учётные записи |
| PATCH | `/api/admin/users/{id}` | подтвердить/отклонить/блокировать |
| DELETE | `/api/admin/users/{id}` | удалить пользователя |

**Важно:** публичный тест (`TestPublic`) **не содержит** `is_correct` — правильные ответы
не уходят клиенту. Проверка всегда на сервере.

---

## 10. Изображения к вопросам

**Хранение:** файлы на диске, `/data/uploads` (env `media_dir` / `MEDIA_DIR`),
метаданные в `media`. На Amvera `/data` — постоянный диск; локально нужен volume `-v`.

**Загрузка `POST /api/media` (multipart, только авторизованные):**

| Проверка | Реализация |
|---|---|
| Размер ≤ **5 МБ** | чтение потоком с обрывом на лимите; повторная проверка в сервисе |
| Формат | **Pillow по содержимому** (magic bytes), не по расширению |
| Белый список | PNG, JPEG, WEBP. **SVG запрещён** (XSS через скрипты) |
| Имя файла | генерируется `<uuid4.hex><ext>`; имя из запроса только в БД |
| Path traversal | `save_path()` резолвит и проверяет, что путь внутри каталога |
| Отдача | `Content-Type` из БД + `X-Content-Type-Options: nosniff` + `inline` |

**Отображение:** `QuestionPublic.image_urls` = `/api/media/{id}`; и в конструкторе,
и при прохождении — компонент **`ImageCarousel.vue`** (одно фото за раз, стрелки,
точки, счётчик, клавиши ← →). Не «сетка всех фото».

**Удаление файлов (важно — хранилище ограничено):**
- вопрос удалён при сохранении теста → `_cleanup_orphan_media()` удаляет файлы,
  пропавшие из новой версии;
- тест удалён → удаляются все его изображения;
- загружено, но не сохранено в тесте → «сирота» до ручной/будущей чистки.

---

## 11. Frontend

**Роуты** (`router.js`, hash history):

| Путь | Компонент | Доступ |
|---|---|---|
| `/login` | `Login.vue` | гость |
| `/profile` | `UserProfile.vue` | авторизация |
| `/editor/:id` | `Constructor.vue` | авторизация |
| `/results/:id` | `Results.vue` | авторизация |
| `/admin` | `Admin.vue` | admin |
| `/take/:token` | `TakeTest.vue` | **публичный** (гард не ждёт сессию) |

**Ключевые файлы:**

- `api.js` — единый клиент: авто-refresh при 401 (с дедупликацией), `downloadFile`,
  `uploadMedia` (multipart без ручного `Content-Type`), русские ошибки из 422.
- `auth.js` — `reactive`-состояние `authState`, `restoreSession()` при старте.
- `constructor/Constructor.vue` — сборка теста; **важно: UUID вопросов и ответов
  сохраняются при редактировании** (не пересоздаются), иначе рвётся связь с попытками;
  `imageIds` переносятся из/в `image_ids`.
- Редакторы по типам: `OneCorrect.vue` (радио инициализируется из `isCorrect`),
  `SomeCorrect.vue`, `TextAnswer.vue`, `MatchAnswers.vue`.
- `ImageUpload.vue` — загрузка/превью-карусель/удаление текущего изображения.
- `TakeTest.vue` — данные участника + ответы; при 404 показывает «тест снят с публикации».

---

## 12. Конфигурация (env)

Чтение через `services/env.py`: **регистронезависимо** (Amvera хранит в UPPER),
с алиасами `MONGO_INITDB_ROOT_USERNAME/PASSWORD/DATABASE`, снятие обрамляющих кавычек.

| Переменная | Назначение | Заметки |
|---|---|---|
| `mongo_host`, `mongo_port`, `mongo_username`, `mongo_password`, `mongo_db_name` | подключение к Mongo | на Amvera — внешняя БД |
| `mongo_auth_source` | где искать пользователя | для root официального образа — `admin` |
| `jwt_secret` | подпись JWT | **≥32 символов**, иначе приложение не стартует |
| `jwt_expire_minutes` / `refresh_token_expire_days` | TTL токенов | 60 / 14 |
| `cookie_secure`, `cookie_samesite` | cookie | на проде `true` / `strict` |
| `admin_username`, `admin_email`, `admin_password` | служебный админ | сильный пароль, иначе падение |
| `log_level`, `log_dir` | логи | `pymongo` приглушён (не пишет ПДн) |
| `media_dir` / `MEDIA_DIR` | каталог файлов | по умолчанию `/data/uploads` |
| `pd_consent_version` | версия согласия ПДн | для аудита |
| `cors_origins` | CORS | в проде пусто (один origin) |

> `.env` **не читать/не печатать** содержимое в диалогах — там секреты.

---

## 13. Развёртывание

**Единый образ — единственный поддерживаемый способ (в т.ч. Amvera).**
`Dockerfile`: stage 1 собирает Vite → stage 2 (python:3.12-slim) ставит зависимости,
nginx отдаёт статику и проксирует `/api` на uvicorn; `docker/start.sh` поднимает
uvicorn в фоне, nginx — на переднем плане.

```bash
docker build -t online-test .
docker run -d --name online-test -p 8080:80 \
  --env-file .env -e mongo_host=host.docker.internal -e mongo_port=27017 \
  -v online_test_media:/data/uploads online-test
```

**Локальная разработка без Docker:** uvicorn :8081 + `npm run dev` :5173 (прокси `/api`).
Vite-прокси нужен, чтобы фронт и API были на одном origin (HttpOnly-cookie, без CORS).

**Amvera:** git push; переменные — в панели; `/data` — постоянный диск (для медиа и логов);
MongoDB внешняя. `docker-compose.yml` на Amvera **не используется**.

---

## 14. Безопасность (сводка)

Реализовано: bcrypt-хэши; JWT в HttpOnly-cookie; refresh с ротацией и `type`-claim;
подтверждение учёток админом; роль при регистрации жёстко `metodist`; защита служебного
админа; rate limiting логина; валидация изображений (magic bytes, лимит, без SVG,
без path traversal); порты БД/backend не публикуются; русские сообщения валидации.

Открытые пункты (см. `docs/security-audit.md`): **TLS** (P0), retention ПДн (P1),
согласие участников-несовершеннолетних (P1), шифрование в покое (P1),
аудит чтения ПДн, CSP, чистка неиспользуемых зависимостей.

---

## 15. Принятые решения (кратко, чтобы не пересматривать вслепую)

1. **Участник без аккаунта** — ФИО + номер сертификата вводятся при прохождении.
2. **Тест — один документ** с встроенными вопросами (embed), не отдельная коллекция.
3. **Правильные ответы не уходят** в публичный API; проверка на сервере.
4. **UUID сохраняются** при редактировании теста — иначе рвётся связь с попытками.
5. **Попытка хранит снимок текстов** — правки/удаление вариантов не искажают историю.
6. **Опубликованный тест неизменяем** (409 + UI-блокировка) — вместо версионности.
7. **Версий теста нет** — сознательно; при необходимости добавить `version: int`.
8. **Изображения — на диске + метаданные в Mongo**, удаляются вместе с вопросом/тестом.
9. **Карусель** для нескольких фото, а не сетка.
10. **Единый Docker-образ** (без compose) — требование Amvera.

---

## 16. Известные ограничения

- Rate limiting **in-memory** — не переживает рестарт и не работает между воркерами.
- **«Сироты»-файлы**: загружено, но не сохранено в тесте → остаётся до чистки.
- **Старые попытки** (до снимка) читаются по id; удалённый вариант → «— вариант удалён —».
- **Нет версионности/истории** тестов, нет откатов.
- **Нет retention** — попытки с ПДн хранятся бессрочно.
- Файл `.env` содержит секреты — не выводить содержимое в переписке.

---

## 17. Как продолжать работу

1. Прочитайте этот файл и `docs/security-audit.md`.
2. Для изменений сверяйтесь с кодом — истина там.
3. Новые модели — в `models/`, контракты — в `schemas/`, логика — в `services/`,
   HTTP — в `routers/`. Не смешивать слои.
4. Фронт: запросы — только через `api.js`; состояние авторизации — через `auth.js`.
5. Обновили поведение (статусы, API, env, структуру) — **обновите этот документ**.
6. Секреты из `.env` не выводить и не обсуждать в переписке.
