"""Тесты M2 (строгий RAG чат-бот): ответ с цитатой, отказ + лог пробела."""

from product.db import models as m
from product.rag import FakeEmbedder
from product.modules import knowledge as kb, chat

EMB = FakeEmbedder()


class FakeProvider:
    """LLM-заглушка: отвечает по фрагментам; маркер отказа — по флагу."""

    def __init__(self, refuse=False):
        self.refuse = refuse

    def call(self, system, messages, tools):
        text = chat.REFUSAL_MARKER if self.refuse else \
            "Эспрессо готовим при 92 градусах. Источник: «Стандарт кофе»."
        return {"text": text, "tool_calls": [], "stop_reason": "end_turn",
                "raw_content": []}


def _seed(db):
    c = m.Company(slug="acme", name="Acme")
    db.add(c)
    db.commit()
    kb.ingest_text(db, c.id, title="Стандарт кофе",
                   content="Эспрессо готовим при температуре 92 градуса.", embedder=EMB)
    return c


def test_answer_with_citation(db):
    c = _seed(db)
    res = chat.answer_question(
        db, c.id, "при какой температуре эспрессо 92 градуса",
        embedder=EMB, llm=FakeProvider())
    assert res["refused"] is False
    assert res["sources"] and res["sources"][0]["document_title"] == "Стандарт кофе"
    # Реплики сохранены (user + assistant).
    assert db.query(m.ChatMessage).count() == 2


def test_retrieval_gate_refuses_and_logs_gap(db):
    c = _seed(db)
    res = chat.answer_question(
        db, c.id, "какой пароль от wifi в офисе компании",
        embedder=EMB, llm=FakeProvider())
    assert res["refused"] is True
    assert res["gap_id"]
    assert db.query(m.QAGap).count() == 1


def test_generation_gate_refuses_when_model_returns_marker(db):
    c = _seed(db)
    # Релевантный документ есть (гейт retrieval пройдёт), но модель «не нашла».
    res = chat.answer_question(
        db, c.id, "при какой температуре эспрессо 92 градуса",
        embedder=EMB, llm=FakeProvider(refuse=True))
    assert res["refused"] is True
    assert res["gap_id"]
    assert db.query(m.QAGap).count() == 1


def test_gaps_are_tenant_scoped(db):
    a = _seed(db)
    b = m.Company(slug="beta", name="Beta")
    db.add(b)
    db.commit()
    chat.answer_question(db, a.id, "нечто чего нет в базе вовсе",
                         embedder=EMB, llm=FakeProvider())
    assert len(chat.list_gaps(db, a.id)) == 1
    assert len(chat.list_gaps(db, b.id)) == 0
