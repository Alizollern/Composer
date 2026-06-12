-- Включаем pgvector в базе evergreen при первом старте контейнера БД.
-- Выполняется автоматически (docker-entrypoint-initdb.d) только на пустом томе.
CREATE EXTENSION IF NOT EXISTS vector;
