"""
Программный запуск миграций Alembic (для старта приложения/контейнера).

Зачем не просто create_all: в проде схему ведёт Alembic — историю изменений
видно, апгрейды воспроизводимы. Но офлайн-разработка и тесты на SQLite не должны
тащить за собой миграционную машинерию, поэтому там остаётся create_all.

`upgrade_to_head()` находит alembic.ini в корне репозитория и накатывает все
ревизии до head на текущую БД (URL берётся из product.config через env.py).
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

# product/db/migrate.py → корень репозитория на два уровня выше.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"


def make_alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    # script_location в ini задан относительно cwd; фиксируем абсолютным путём,
    # чтобы upgrade работал из любой рабочей директории (в т.ч. в контейнере).
    cfg.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
    return cfg


def upgrade_to_head() -> None:
    """Накатить все миграции до последней ревизии."""
    command.upgrade(make_alembic_config(), "head")
