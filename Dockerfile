# Composer AI — бэкенд (FastAPI + движок агентов) в одном контейнере.
# Агенты НЕ требуют отдельных контейнеров: их "мозг" — Claude API (удалённо),
# а локально это лёгкий цикл, который крутится в одном процессе.

FROM python:3.11-slim

# Не пишем .pyc, логи сразу в stdout (видно в docker logs).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости — слой кэшируется, пересборка быстрее.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Затем код проекта.
COPY . .

EXPOSE 8000

# ANTHROPIC_API_KEY передаётся через окружение (см. docker-compose.yml),
# НИКОГДА не зашивается в образ.
CMD ["python", "-m", "uvicorn", "composer.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
