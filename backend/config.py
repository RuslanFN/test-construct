


import logging
import os

from dotenv import load_dotenv

from services.env import getenv

load_dotenv()

# Каталог логов настраивается; на Amvera удобно писать в persistentMount (/data),
# иначе путь '/app/backend/logs' живёт только до перезапуска контейнера.
_log_dir = getenv('log_dir', 'logs') or 'logs'
os.makedirs(_log_dir, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(_log_dir, 'logs.txt'), mode='a', encoding='utf-8')

stream_handler = logging.StreamHandler()

# Уровень логов настраивается (на проде — INFO/WARNING без дампов ПДн).
_log_level_name = (getenv('log_level', 'INFO') or 'INFO').upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        file_handler,
        stream_handler
    ])

# pymongo в DEBUG пишет полные документы (ФИО, данные участников) — приглушаем.
logging.getLogger('pymongo').setLevel(max(_log_level, logging.WARNING))

# JWT

secret_key = getenv('jwt_secret') or ''
if not secret_key or secret_key == 'change-me-in-env' or len(secret_key) < 32:
    raise RuntimeError(
        'Не задан корректный jwt_secret. Укажите в .env случайную строку >= 32 символов. '
        'Сгенерировать: python -c "import secrets;print(secrets.token_urlsafe(48))"'
    )
jwt_algorithm = 'HS256'

access_token_expire_minutes = int(getenv('jwt_expire_minutes', '60'))
# Время жизни refresh-токена (дней). Пока он валиден — сессию можно
# продлевать без повторного ввода пароля.

refresh_token_expire_days = int(getenv('refresh_token_expire_days', '14'))

# HttpOnly-cookie с токеном

cookie_name = getenv('cookie_name', 'access_token')
# Отдельная HttpOnly-кука для refresh-токена (используется только эндпоинтом /refresh)

refresh_cookie_name = getenv('refresh_cookie_name', 'refresh_token')
# Secure по умолчанию включён (нужен HTTPS). В dev для http явно ставят cookie_secure=false.

cookie_secure = getenv('cookie_secure', 'true').lower() == 'true'
# SameSite=Strict по умолчанию (защита от CSRF). lax — если нужен переход по внешней ссылке.

cookie_samesite = getenv('cookie_samesite', 'strict').lower()
cookie_max_age = access_token_expire_minutes * 60
refresh_cookie_max_age = refresh_token_expire_days * 24 * 60 * 60

# Версия текста согласия на обработку ПДн (для аудита: какой документ принял пользователь)

pd_consent_version = getenv('pd_consent_version', '1.0')

# Администратор, создаётся при запуске, если ещё не существует



admin_username = getenv('admin_username', 'admin')
admin_email = getenv('admin_email', 'admin@example.com')
admin_password = getenv('admin_password') or ''
if not admin_password or admin_password == 'admin12345':
    raise RuntimeError(
        'Не задан корректный admin_password. Укажите в .env надёжный пароль администратора.'
    )

# HTTP-прокси перед приложением (определение IP клиента)

# Заголовок, из которого берём реальный IP клиента. ВАЖНО: доверять можно только
# заголовку, который ставит ТОЛЬКО доверенный прокси и который он перезаписывает
# (клиентский вариант отбрасывается). По умолчанию пусто = не доверяем никаким
# заголовкам и берём адрес сокета (безопасно, подделка невозможна).
#   Amvera (Envoy):          trusted_client_ip_header=x-envoy-external-address
#   свой nginx с real_ip:     trusted_client_ip_header=x-real-ip
#   прокси с XFF:             trusted_client_ip_header=x-forwarded-for  (берётся ПОСЛЕДНИЙ адрес)
#   прямой доступ:            (пусто)
trusted_client_ip_header = (getenv('trusted_client_ip_header', '') or '').strip().lower()

# Разрешённые источники для CORS (через запятую). В проде за nginx (один origin)
# CORS не нужен — оставьте пустым. Пример: http://localhost:5173,http://127.0.0.1:5173
cors_origins = [o.strip() for o in getenv('cors_origins', '').split(',') if o.strip()]

# Капча «я не робот» (арифметика словами, ответ цифрами)
# Время жизни задачи, сек. Капча на отправку теста показывается в конце (по кнопке),
# поэтому её решают сразу — короткий TTL достаточен.
captcha_ttl_seconds = int(getenv('captcha_ttl_seconds', '600'))
# Минимальное время решения, сек: ответ быстрее порога считается ботом.
# 1 сек: человек не успевает прочитать пример и набрать ответ.
captcha_min_seconds = float(getenv('captcha_min_seconds', '1'))
