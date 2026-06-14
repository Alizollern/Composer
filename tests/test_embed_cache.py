"""Кэш эмбеддингов: один и тот же текст не должен повторно гонять модель,
и кэш не должен менять сам вектор."""

from typing import List

from product.rag.embedder import CachingEmbedder, Embedder, FakeEmbedder


class CountingEmbedder(Embedder):
    """Считает, сколько ТЕКСТОВ реально посчитано базовым эмбеддером."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        self.calls = 0          # число вызовов embed()
        self.texts_embedded = 0  # число реально посчитанных текстов
        self._inner = FakeEmbedder(dim=dim)

    def embed(self, texts: List[str]) -> List[List[float]]:
        self.calls += 1
        self.texts_embedded += len(texts)
        return self._inner.embed(texts)


def test_repeated_text_hits_cache():
    base = CountingEmbedder()
    emb = CachingEmbedder(base)

    v1 = emb.embed_one("как часто протирать тренажёры")
    v2 = emb.embed_one("как часто протирать тренажёры")

    # модель посчитала текст только один раз
    assert base.texts_embedded == 1
    # вектор идентичен (кэш не портит результат)
    assert v1 == v2


def test_cache_matches_uncached_result():
    base = CountingEmbedder()
    emb = CachingEmbedder(base)
    text = "возврат денег за абонемент"

    cached = emb.embed_one(text)
    fresh = FakeEmbedder(dim=base.dim).embed_one(text)

    assert cached == fresh


def test_batch_computes_only_misses():
    base = CountingEmbedder()
    emb = CachingEmbedder(base)

    emb.embed(["а", "б"])           # оба новые → 2
    emb.embed(["б", "в", "а"])      # только «в» новый → +1

    assert base.texts_embedded == 3


def test_duplicate_in_one_batch_counted_once():
    base = CountingEmbedder()
    emb = CachingEmbedder(base)

    out = emb.embed(["повтор", "повтор", "повтор"])

    assert base.texts_embedded == 1
    assert out[0] == out[1] == out[2]


def test_different_dim_does_not_collide():
    # Разные «подписи» эмбеддера не должны делить кэш.
    a = CachingEmbedder(FakeEmbedder(dim=32))
    b = CachingEmbedder(FakeEmbedder(dim=64))
    va = a.embed_one("текст")
    vb = b.embed_one("текст")
    assert len(va) == 32
    assert len(vb) == 64
