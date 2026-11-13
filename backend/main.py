from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uvicorn import run

import config  # noqa: F401  (настраивает логирование)
import db
import seed
from routers import auth_router, public_router, tests_router, admin_router


# Перевод типовых сообщений валидации Pydantic на русский
_VALIDATION_RU = {
    'Field required': 'Поле обязательно для заполнения',
    'Input should be a valid string': 'Ожидается строка',
    'Input should be a valid boolean': 'Ожидается логическое значение (да/нет)',
    'Input should be a valid integer': 'Ожидается целое число',
    'Input should be a valid email address': 'Некорректный формат электронной почты',
    'String should have at least 8 characters': 'Пароль должен содержать минимум 8 символов',
    'String should have at least 3 characters': 'Логин должен содержать минимум 3 символа',
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.ensure_indexes()
    await seed.ensure_admin()
    yield
    await db.close_client()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = err.get('loc', [])
        field = loc[-1] if loc else ''
        msg = err.get('msg', 'Некорректное значение')
        # сообщения из наших validator'ов начинаются с "Value error, "
        if msg.startswith('Value error, '):
            msg = msg[len('Value error, '):]
        msg = _VALIDATION_RU.get(msg, msg)
        errors.append({'field': str(field), 'message': msg})
    # detail — строка, склеенная из сообщений (фронт покажет её как есть)
    text = '; '.join(e['message'] for e in errors) or 'Некорректные данные'
    return JSONResponse(
        status_code=422,
        content={'detail': text, 'errors': errors},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth_router)
app.include_router(tests_router)
app.include_router(public_router)
app.include_router(admin_router)


@app.get('/api/health')
async def health():
    return {'status': 'ok'}


if __name__ == "__main__":
    run(app, host="127.0.0.1", port=8081)

