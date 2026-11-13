#!/usr/bin/env bash
# Запуск единого контейнера: backend (uvicorn) + nginx (фронт + прокси /api)
set -euo pipefail

cd /app/backend

# Стартуем backend в фоне на localhost:8081
uvicorn main:app --host 127.0.0.1 --port 8081 --workers "${UVICORN_WORKERS:-1}" &
BACKEND_PID=$!

# Ждём старта backend, не дольше ~30с
for i in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:8081/api/health >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend failed to start" >&2
    exit 1
fi

# Graceful shutdown при остановке контейнера
cleanup() {
    kill "$BACKEND_PID" 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
}
trap cleanup TERM INT

# nginx на переднем плане
nginx -g 'daemon off;' &
NGINX_PID=$!

# Ждём завершения любого процесса
wait -n "$BACKEND_PID" "$NGINX_PID" 2>/dev/null || true

# Если один упал — гасим второй
kill "$BACKEND_PID" 2>/dev/null || true
kill "$NGINX_PID" 2>/dev/null || true
