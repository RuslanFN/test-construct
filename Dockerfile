# ============================================================
#  Единый образ для Amvera: frontend (Vue→nginx) + backend (FastAPI)
#  Один контейнер, наружу порт 80 (nginx), /api → uvicorn на 127.0.0.1:8081
# ============================================================

# ---------- stage 1: сборка фронтенда ----------
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/online_test/package.json frontend/online_test/package-lock.json ./
RUN npm ci
COPY frontend/online_test/ ./
RUN npm run build

# ---------- stage 2: runtime (python + nginx) ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# nginx, curl (healthcheck/start.sh), зависимости сборки bcrypt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        nginx curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# ---------- backend ----------
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
RUN mkdir -p logs

# ---------- frontend (собранная статика) ----------
COPY --from=frontend-build /fe/dist /usr/share/nginx/html

# ---------- nginx + скрипт запуска ----------
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# убираем дефолтный конфиг, чтобы не конфликтовал
RUN rm -f /etc/nginx/sites-enabled/default
COPY docker/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1/api/health || exit 1

# Рабочая директория для запуска backend (path logs/ относительный)
WORKDIR /app/backend
CMD ["/usr/local/bin/start.sh"]
