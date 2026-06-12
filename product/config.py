"""
Конфигурация продукта Evergreen (отдельно от composer/config.py).

Здесь — настройки SaaS-слоя: БД, хранилище файлов, секреты auth. Всё через env,
с разумными дефолтами для локальной разработки. Движок про это не знает.
"""

import os

# ---- База данных (PostgreSQL + pgvector) ----
# Пример: postgresql+psycopg://user:pass@localhost:5432/evergreen
DATABASE_URL = os.environ.get(
    "EVERGREEN_DATABASE_URL",
    "postgresql+psycopg://localhost:5432/evergreen",
)
# Размерность эмбеддингов для RAG. ДОЛЖНА совпадать с размерностью выбранной
# модели эмбеддингов (GeminiEmbedder text-embedding-004 → 768; FakeEmbedder → 256).
# Под это значение создаётся pgvector-колонка chunks.embedding_vec, поэтому при
# смене модели нужна новая миграция/реиндексация.
EMBEDDING_DIM = int(os.environ.get("EVERGREEN_EMBEDDING_DIM", "768"))

# pgvector-ускорение поиска на Postgres. Выключение (=0) форсит Python-косинус
# (полезно для отладки/сравнения). На SQLite флаг игнорируется — там всегда косинус.
PGVECTOR_ENABLED = os.environ.get("EVERGREEN_PGVECTOR", "1").strip().lower() not in (
    "0", "false", "no", "")

# ---- Файловое хранилище оригиналов документов ----
# Backend: "local" (папка на диске) или "s3" (S3-совместимое объектное хранилище).
# Пусто → авто: s3, если задан S3_ENDPOINT, иначе local.
STORAGE_BACKEND = os.environ.get("EVERGREEN_STORAGE_BACKEND", "")
# Папка для local-хранилища (dev/тесты).
STORAGE_DIR = os.environ.get("EVERGREEN_STORAGE_DIR", "var/storage")
# S3-совместимое хранилище (прод): AWS S3 / MinIO / Yandex Object Storage.
S3_ENDPOINT = os.environ.get("EVERGREEN_S3_ENDPOINT", "")
S3_BUCKET = os.environ.get("EVERGREEN_S3_BUCKET", "evergreen-docs")
S3_ACCESS_KEY = os.environ.get("EVERGREEN_S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("EVERGREEN_S3_SECRET_KEY", "")
S3_REGION = os.environ.get("EVERGREEN_S3_REGION", "us-east-1")

# ---- Аутентификация ----
# В проде ОБЯЗАТЕЛЬНО задать через env. Дефолт — только для локалки.
JWT_SECRET = os.environ.get("EVERGREEN_JWT_SECRET", "dev-only-change-me")
JWT_TTL_HOURS = int(os.environ.get("EVERGREEN_JWT_TTL_HOURS", "24"))

# ---- Интеграции ----
TELEGRAM_BOT_TOKEN = os.environ.get("EVERGREEN_TELEGRAM_BOT_TOKEN", "")
