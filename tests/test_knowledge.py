"""Тесты M1 (база знаний): приём, поиск, версионирование, изоляция тенантов."""

import pytest

from product.db import models as m
from product.rag import FakeEmbedder, search_chunks
from product.modules import knowledge as kb

EMB = FakeEmbedder()


def _company(db, slug):
    c = m.Company(slug=slug, name=slug.title())
    db.add(c)
    db.commit()
    return c


def test_ingest_creates_version_and_chunks(db):
    c = _company(db, "acme")
    doc = kb.ingest_text(
        db, c.id, title="Стандарт кофе",
        content="Эспрессо готовим при температуре 92 градуса. Молоко до 65.",
        category="barista", embedder=EMB)
    assert doc.status == m.DOC_PUBLISHED
    assert doc.current_version_id
    chunks = db.query(m.Chunk).filter_by(document_id=doc.id).all()
    assert len(chunks) >= 1
    assert all(ch.embedding for ch in chunks)


def test_search_finds_relevant_document(db):
    c = _company(db, "acme")
    kb.ingest_text(db, c.id, title="Стандарт кофе",
                   content="Эспрессо готовим при температуре 92 градуса.", embedder=EMB)
    kb.ingest_text(db, c.id, title="Уборка",
                   content="Зал убираем каждый вечер после закрытия.", embedder=EMB)
    hits = search_chunks(db, c.id, EMB.embed_one("температура эспрессо"), top_k=3)
    assert hits
    assert hits[0].document_title == "Стандарт кофе"


def test_new_version_reindexes_chunks(db):
    c = _company(db, "acme")
    doc = kb.ingest_text(db, c.id, title="Стандарт",
                         content="Старый текст про 92 градуса.", embedder=EMB)
    v2 = kb.add_version(db, c.id, doc.id, content="Новый текст про 90 градусов.",
                        embedder=EMB)
    chunks = db.query(m.Chunk).filter_by(document_id=doc.id).all()
    assert chunks and all(ch.version_id == v2.id for ch in chunks)
    db.refresh(doc)
    assert doc.current_version_id == v2.id
    # История версий сохранена.
    assert db.query(m.DocumentVersion).filter_by(document_id=doc.id).count() == 2


def test_status_transitions(db):
    c = _company(db, "acme")
    doc = kb.ingest_text(db, c.id, title="Док", content="текст", publish=False, embedder=EMB)
    assert doc.status == m.DOC_DRAFT
    kb.set_status(db, c.id, doc.id, m.DOC_PUBLISHED)
    db.refresh(doc)
    assert doc.status == m.DOC_PUBLISHED
    with pytest.raises(ValueError):
        kb.set_status(db, c.id, doc.id, "bogus")


def test_tenant_isolation_in_search(db):
    a = _company(db, "acme")
    b = _company(db, "beta")
    kb.ingest_text(db, a.id, title="Секрет A",
                   content="Пароль сейфа компании A: 1234.", embedder=EMB)
    # Компания B ищет тем же запросом — не должна видеть документ A.
    hits = search_chunks(db, b.id, EMB.embed_one("пароль сейфа"), top_k=5)
    assert hits == []


def test_get_document_rejects_foreign(db):
    a = _company(db, "acme")
    b = _company(db, "beta")
    doc = kb.ingest_text(db, a.id, title="A", content="текст", embedder=EMB)
    with pytest.raises(KeyError):
        kb.get_document(db, b.id, doc.id)
