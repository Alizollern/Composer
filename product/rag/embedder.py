"""
Шов эмбеддингов: текст → вектор.

Весь RAG зависит только от интерфейса Embedder, а не от конкретной модели.
  * GeminiEmbedder — прод (бесплатные эмбеддинги Google AI Studio).
  * FakeEmbedder   — офлайн-разработка и тесты: детерминированный хеш-вектор,
    без сети. Совпадающие слова дают высокий косинус — этого достаточно, чтобы
    проверять логику поиска/цитирования без живой модели.

get_embedder() выбирает реализацию по окружению: есть ключ Gemini и провайдер
gemini → Gemini; иначе → Fake. Тесты могут передать FakeEmbedder напрямую.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from abc import ABC, abstractmethod
from typing import List

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class Embedder(ABC):
    """Контракт эмбеддера. dim — размерность вектора (постоянна для реализации)."""

    dim: int

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Векторизовать список текстов (батч). Длина результата == длине входа."""
        ...

    def embed_one(self, text: str) -> List[float]:
        return self.embed([text])[0]


class FakeEmbedder(Embedder):
    """Детерминированный эмбеддер без сети (хеширование «мешка слов»).

    Каждое слово стабильно (sha1, не солёный hash()) отображается в индекс
    вектора фиксированной размерности; частоты нормируются по L2. Тексты с общими
    словами получают высокий косинус — ровно то, что нужно для офлайн-тестов RAG.
    Воспроизводим между запусками и машинами.
    """

    def __init__(self, dim: int = 256):
        self.dim = dim

    def _hash_idx(self, token: str) -> int:
        h = hashlib.sha1(token.encode("utf-8")).digest()
        return int.from_bytes(h[:4], "big") % self.dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        out: List[List[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _tokenize(text):
                vec[self._hash_idx(tok)] += 1.0
            out.append(_l2_normalize(vec))
        return out


class GeminiEmbedder(Embedder):
    """Прод-эмбеддер на бесплатных эмбеддингах Google AI Studio.

    Использует тот же SDK google-genai, что и LLM-провайдер. Ключ — из
    GEMINI_API_KEY/GOOGLE_API_KEY. Размерность задаётся моделью (text-embedding-004
    → 768). Векторы L2-нормируем для устойчивого косинуса.
    """

    def __init__(self, model: str | None = None, dim: int = 768):
        from google import genai  # импорт ленивый: офлайн без пакета не падаем
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key) if key else genai.Client()
        self.model = model or os.environ.get(
            "EVERGREEN_EMBEDDING_MODEL", "text-embedding-004")
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        resp = self.client.models.embed_content(model=self.model, contents=texts)
        vecs = [list(e.values) for e in resp.embeddings]
        return [_l2_normalize(v) for v in vecs]


def get_embedder() -> Embedder:
    """Выбрать эмбеддер по окружению.

    EVERGREEN_EMBEDDER=fake|gemini форсирует выбор. Иначе: gemini, если задан
    ключ Gemini (прод); по умолчанию — Fake (офлайн/тесты, без сети)."""
    choice = os.environ.get("EVERGREEN_EMBEDDER", "").strip().lower()
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if choice == "gemini" or (choice == "" and has_key):
        return GeminiEmbedder()
    return FakeEmbedder()
