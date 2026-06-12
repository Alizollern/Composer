# Evergreen — образ приложения (FastAPI + движок + собранный фронт).
# Мультистейдж: сначала собираем фронт в node, потом кладём в python-рантайм.

# ---- Этап 1: сборка фронтенда ----
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # -> /fe/dist

# ---- Этап 2: python-рантайм ----
FROM python:3.11-slim

# Не пишем .pyc, логи сразу в stdout (видно в docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пересборка быстрее.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код проекта.
COPY . .

# Свежесобранный фронт из первого этапа (перекрывает закоммиченный dist).
COPY --from=frontend /fe/dist ./frontend/dist

EXPOSE 8000

# Секреты (ANTHROPIC_API_KEY / GEMINI_API_KEY) приходят через окружение
# из docker-compose, в образ НИКОГДА не зашиваются.
CMD ["python", "-m", "uvicorn", "product.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
