"""Юнит-тесты RAG-инфраструктуры: чанкинг, эмбеддер, косинус."""

from product.rag import chunk_text, FakeEmbedder, cosine


def test_chunking_splits_long_text():
    text = "\n\n".join(f"Абзац номер {i} с каким-то содержимым." for i in range(50))
    chunks = chunk_text(text, target_words=40, overlap_words=8)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_chunking_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_fake_embedder_is_deterministic():
    emb = FakeEmbedder()
    v1 = emb.embed_one("температура эспрессо 92 градуса")
    v2 = emb.embed_one("температура эспрессо 92 градуса")
    assert v1 == v2
    assert len(v1) == emb.dim


def test_cosine_related_beats_unrelated():
    emb = FakeEmbedder()
    q = emb.embed_one("при какой температуре варить эспрессо")
    related = emb.embed_one("эспрессо варим при температуре 92 градуса")
    unrelated = emb.embed_one("график уборки зала по вечерам в субботу")
    assert cosine(q, related) > cosine(q, unrelated)


def test_cosine_edge_cases():
    assert cosine([], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
