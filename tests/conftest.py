"""
Общие фикстуры тестов Evergreen.

Всё работает ОФЛАЙН и детерминированно:
  * БД — SQLite в памяти (без Postgres-сервера);
  * эмбеддер — FakeEmbedder (форсим через env EVERGREEN_EMBEDDER=fake);
  * LLM — не зовём по сети: в API-клиенте подменяем brain.complete фейком,
    который отвечает по переданным фрагментам.

Так проверяется вся логика продукта (RAG, гейты, RBAC, изоляция тенантов),
не завися ни от сети, ни от ключей.
"""

import os
import tempfile

import pytest

# Форсим офлайн-эмбеддер ДО импорта продуктовых модулей.
os.environ["EVERGREEN_EMBEDDER"] = "fake"
# Тесты не должны писать журнал агента в рабочую директорию — выключаем его.
os.environ["EVERGREEN_AGENT_LOG_ENABLED"] = "0"
os.environ.setdefault("EVERGREEN_JWT_SECRET", "test-secret")
# Хранилище оригиналов — локальная папка во временном каталоге (изолированно,
# чтобы тесты не писали в рабочую директорию репозитория).
os.environ["EVERGREEN_STORAGE_BACKEND"] = "local"
os.environ.setdefault(
    "EVERGREEN_STORAGE_DIR", tempfile.mkdtemp(prefix="evergreen-test-storage-"))

from fastapi.testclient import TestClient  # noqa: E402

from product.db.session import make_engine, make_session_factory, init_db  # noqa: E402
from product.auth.deps import get_db  # noqa: E402
from product.api.app import create_app  # noqa: E402
from product import brain  # noqa: E402
from product.modules import chat as chat_module  # noqa: E402


@pytest.fixture()
def engine():
    """Изолированный in-memory SQLite на каждый тест (StaticPool, общая память)."""
    from sqlalchemy.pool import StaticPool
    from sqlalchemy import create_engine
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    init_db(eng)
    return eng


@pytest.fixture()
def session_factory(engine):
    return make_session_factory(engine)


@pytest.fixture()
def db(session_factory):
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


_FAKE_QUIZ_JSON = (
    '[{"question": "Какова температура эспрессо?", '
    '"options": ["80", "92", "100", "60"], "correct_index": 1, '
    '"source_quote": "Эспрессо готовим при температуре 92 градуса."}]'
)


def _fake_complete(system, user, *, llm=None, **_):
    """Детерминированная замена LLM:
      * запрос на генерацию теста (M3) — возвращает валидный JSON-массив;
      * запрос разбора отзыва (M4) — JSON-объект (тональность/жалоба по оценке);
      * запрос чат-бота (M2) с фрагментами — ответ со ссылкой;
      * иначе — маркер отказа (для негативных тестов; обычно retrieval-гейт
        срабатывает раньше и сюда не доходит)."""
    if "проверочный тест" in system:
        return _FAKE_QUIZ_JSON
    if "операционный директор" in system:
        import json as _json
        import re as _re
        mm = _re.search(r"Оценка клиента: (\d)", user)
        rating = int(mm.group(1)) if mm else 0
        if rating >= 4:
            sentiment, complaint = "positive", False
        elif rating == 3:
            sentiment, complaint = "neutral", False
        else:
            sentiment, complaint = "negative", True
        return _json.dumps({
            "sentiment": sentiment, "topic": "Тест",
            "is_complaint": complaint,
            "recommendation": "Устранить причину жалобы" if complaint else "",
        }, ensure_ascii=False)
    if "Фрагмент 1" in user:
        return "Согласно стандартам компании, ответ найден. Источник: «стандарт»."
    return chat_module.REFUSAL_MARKER


@pytest.fixture()
def client(session_factory, monkeypatch):
    """TestClient с БД из теста и офлайн-LLM (brain.complete подменён)."""
    app = create_app()

    def _override_get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    monkeypatch.setattr(brain, "complete", _fake_complete)
    return TestClient(app)
