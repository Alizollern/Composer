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
from sqlalchemy import create_engine, inspect

from product.config import DATABASE_URL
from product.db.models import Base

# product/db/migrate.py → корень репозитория на два уровня выше.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI = _REPO_ROOT / "alembic.ini"


def make_alembic_config() -> Config:
    cfg = Config(str(_ALEMBIC_INI))
    # script_location в ini задан относительно cwd; фиксируем абсолютным путём,
    # чтобы upgrade работал из любой рабочей директории (в т.ч. в контейнере).
    cfg.set_main_option("script_location", str(_REPO_ROOT / "alembic"))
    return cfg


class OrphanSchemaError(RuntimeError):
    """БД содержит схему без отметки Alembic, и схема НЕ совпадает с актуальной —
    автоштамповать опасно (можно «потерять» недостающие таблицы/колонки)."""


def _orphan_status(url: str) -> str:
    """Определить состояние БД относительно Alembic.

    Возвращает:
      * "tracked"  — есть alembic_version (нормальный путь, просто upgrade);
      * "fresh"    — пустая БД (нет даже companies) — upgrade создаст всё с нуля;
      * "stampable"— схема есть, отметки нет, и она СОВПАДАЕТ с текущими моделями
                     (типично для старого create_all) — безопасно проштамповать;
      * "orphan"   — схема есть, отметки нет, но она НЕ полна — нужна ручная
                     разборка (для dev — пересоздать том)."""
    engine = create_engine(url, future=True)
    try:
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        if "alembic_version" in tables:
            return "tracked"
        if "companies" not in tables:
            return "fresh"
        # Схема есть, но Alembic про неё не знает. Безопасно штамповать, только
        # если все таблицы текущих моделей уже присутствуют (полная схема).
        expected = set(Base.metadata.tables.keys())
        if expected.issubset(tables):
            return "stampable"
        return "orphan"
    finally:
        engine.dispose()


def upgrade_to_head() -> None:
    """Привести схему БД к последней ревизии — устойчиво к «осиротевшей» базе.

    Главное: при старте контейнера НЕ падать в крэш-луп, если БД уже содержит
    схему, но не помечена Alembic'ом. Если схема полна — штампуем и идём дальше;
    если неполна — бросаем понятную ошибку, а не молча ломаем данные."""
    cfg = make_alembic_config()
    status = _orphan_status(DATABASE_URL)
    if status == "stampable":
        command.stamp(cfg, "head")
    elif status == "orphan":
        raise OrphanSchemaError(
            "База данных содержит частичную схему без отметки Alembic. "
            "Это бывает от старого запуска. Для разработки пересоздайте том: "
            "`docker compose down -v && docker compose up --build`. "
            "Если в базе важные данные — нужна ручная миграция."
        )
    command.upgrade(cfg, "head")
