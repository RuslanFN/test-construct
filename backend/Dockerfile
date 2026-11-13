# Backend: FastAPI + uvicorn + PyMongo Async
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /app

# Минимальные системные зависимости (для сборки bcrypt и т.п.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Ставим зависимости отдельным слоем (кэшируется при изменении только кода)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

RUN mkdir -p logs

EXPOSE 8081

# Healthcheck на /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8081/api/health || exit 1

# В контейнере слушаем 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
