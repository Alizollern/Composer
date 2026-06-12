"""
Движок и сессии БД.

Один и тот же код работает на двух СУБД:
  * PostgreSQL — прод (env EVERGREEN_DATABASE_URL, напр.
    postgresql+psycopg://evergreen:evergreen@db:5432/evergreen);
  * SQLite — офлайн-разработка и тесты (быстро, без сервера).

Выбор СУБД — это конфиг, а не код: модели и репозитории про диалект не знают.
Тесты поднимают изолированную in-memory/файловую SQLite через make_engine().
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from product.config import DATABASE_URL
from product.db.models import Base


def make_engine(url: str | None = None, *, echo: bool = False) -> Engine:
    """Создать engine. SQLite требует особого флага для многопоточного доступа
    (FastAPI отдаёт запросы из пула потоков), у Postgres этого нет."""
    url = url or DATABASE_URL
    kwargs: dict = {"echo": echo, "future": True}
    if url.startswith("sqlite"):
        # check_same_thread=False — иначе SQLite ругается на доступ из разных потоков.
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Фабрика сессий, привязанная к engine. expire_on_commit=False — чтобы
    объекты оставались пригодными к чтению после commit (удобно в API-ответах)."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine: Engine) -> None:
    """Создать таблицы по моделям. В проде роль миграций берёт Alembic; для
    офлайн-разработки и тестов достаточно create_all."""
    Base.metadata.create_all(engine)


# --- Глобальные engine/SessionLocal для приложения (ленивая инициализация) ---
# Тесты НЕ используют эти глобали — они строят свой engine через make_engine().
_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = make_session_factory(get_engine())
    return _SessionLocal


def session_scope() -> Session:
    """Открыть новую сессию приложения. Вызывающий обязан её закрыть
    (в API это делает FastAPI-зависимость get_db через try/finally)."""
    return get_session_factory()()
