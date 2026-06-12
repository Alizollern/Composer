"""
Среда выполнения миграций Alembic для Evergreen.

URL базы и метаданные берём из самого приложения (единый источник правды):
  * target_metadata = product.db.models.Base.metadata — autogenerate видит модели;
  * URL = product.config.DATABASE_URL (env EVERGREEN_DATABASE_URL).

Так миграции и приложение всегда смотрят на одну и ту же схему и одну БД.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from product.config import DATABASE_URL
from product.db.models import Base

config = context.config
# URL не из ini, а из конфига приложения — чтобы не дублировать секрет.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Сгенерировать SQL без подключения к БД (alembic upgrade --sql)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Применить миграции через живое подключение."""
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = DATABASE_URL
    connectable = engine_from_config(
        cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
