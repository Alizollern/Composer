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
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
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
    GEMINI_API_KEY/GOOGLE_API_KEY.

    Модель по умолчанию — `gemini-embedding-001` (актуальная в API v1beta; старая
    `text-embedding-004` для новых ключей уже отдаёт 404). У этой модели размерность
    настраиваемая, поэтому мы явно запрашиваем output_dimensionality = self.dim,
    чтобы вектор совпадал с размером pgvector-колонки (EVERGREEN_EMBEDDING_DIM).
    При размерности ≠ 3072 Google не нормирует вектор сам — нормируем L2 здесь.
    """

    def __init__(self, model: str | None = None, dim: int | None = None):
        from google import genai  # импорт ленивый: офлайн без пакета не падаем
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=key) if key else genai.Client()
        self.model = model or os.environ.get(
            "EVERGREEN_EMBEDDING_MODEL", "gemini-embedding-001")
        # Размер берём из конфига, чтобы он совпадал с pgvector-колонкой.
        if dim is None:
            from product.config import EMBEDDING_DIM
            dim = EMBEDDING_DIM
        self.dim = dim

    def embed(self, texts: List[str]) -> List[List[float]]:
        from google.genai import types
        resp = self.client.models.embed_content(
            model=self.model, contents=texts,
            config=types.EmbedContentConfig(output_dimensionality=self.dim))
        vecs = [list(e.values) for e in resp.embeddings]
        return [_l2_normalize(v) for v in vecs]


# --- Кэш эмбеддингов --------------------------------------------------------
# Эмбеддинг — чистая функция от текста: один и тот же текст всегда даёт один и
# тот же вектор. Значит, повторные запросы (один вопрос боту, поиск Опер-дира по
# стандартам) можно не гонять в платную модель, а брать из памяти. Это режет и
# счёт за API, и задержку. Кэш общий между запросами (модульный) и
# потокобезопасный — Опер-дир считает в фоновом потоке. Размер ограничен (LRU),
# чтобы массовый ingest не раздул память. Ключ включает «подпись» эмбеддера
# (класс+модель+размерность), чтобы вектора разных моделей не смешались.

_CACHE: "OrderedDict[tuple, List[float]]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_MAX = int(os.environ.get("EVERGREEN_EMBED_CACHE_MAX", "4096"))


class CachingEmbedder(Embedder):
    """Обёртка над любым эмбеддером с кэшом «текст → вектор».

    Прозрачна: при промахе считает базовым эмбеддером, как раньше. Никогда не
    меняет результат — только избегает повторных вызовов на тот же текст.
    """

    def __init__(self, base: Embedder):
        self.base = base
        self.dim = base.dim
        self._sig = (type(base).__name__,
                     getattr(base, "model", ""), base.dim)

    def _key(self, text: str) -> tuple:
        return (self._sig, text)

    def embed(self, texts: List[str]) -> List[List[float]]:
        results: List[List[float]] = [None] * len(texts)  # type: ignore[list-item]
        misses: List[str] = []
        miss_pos: List[int] = []

        with _CACHE_LOCK:
            for i, text in enumerate(texts):
                key = self._key(text)
                hit = _CACHE.get(key)
                if hit is not None:
                    _CACHE.move_to_end(key)        # отметить как недавно нужный
                    results[i] = hit
                else:
                    misses.append(text)
                    miss_pos.append(i)

        if misses:
            # один и тот же текст в батче считаем один раз
            uniq = list(dict.fromkeys(misses))
            fresh = self.base.embed(uniq)
            vec_by_text = dict(zip(uniq, fresh))
            with _CACHE_LOCK:
                for text in uniq:
                    _CACHE[self._key(text)] = vec_by_text[text]
                    _CACHE.move_to_end(self._key(text))
                while len(_CACHE) > _CACHE_MAX:
                    _CACHE.popitem(last=False)      # выкинуть самый старый
            for pos, text in zip(miss_pos, misses):
                results[pos] = vec_by_text[text]

        return results


def get_embedder() -> Embedder:
    """Выбрать эмбеддер по окружению.

    EVERGREEN_EMBEDDER=fake|gemini форсирует выбор. Иначе: gemini, если задан
    ключ Gemini (прод); по умолчанию — Fake (офлайн/тесты, без сети).
    Результат оборачивается в кэш (EVERGREEN_EMBED_CACHE=0 отключает)."""
    choice = os.environ.get("EVERGREEN_EMBEDDER", "").strip().lower()
    has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if choice == "gemini" or (choice == "" and has_key):
        base: Embedder = GeminiEmbedder()
    else:
        base = FakeEmbedder()
    if os.environ.get("EVERGREEN_EMBED_CACHE", "1").strip().lower() in ("0", "false", "no"):
        return base
    return CachingEmbedder(base)
