"""
product/rag — поиск по базе знаний (Retrieval-Augmented Generation).

Инфраструктура, общая для модулей M1 (база знаний) и M2 (чат-бот). Три шва:

  * embedder — превращает текст в вектор. Прод: Gemini-эмбеддинги; офлайн/тесты:
    детерминированный FakeEmbedder (без сети, воспроизводимо). Подмена через env.
  * chunking — режет длинный документ на куски разумного размера с нахлёстом.
  * search — косинусная близость по чанкам компании; top-k кандидатов для ответа.

Принцип строгого RAG (ТЗ): бот отвечает ТОЛЬКО тем, что нашлось в базе знаний
компании, и ссылается на источник. Не нашлось — честный отказ + лог пробела.
Здесь живёт «retrieval»; «generation» с этим контрактом — в модуле M2.
"""

from product.rag.embedder import Embedder, FakeEmbedder, GeminiEmbedder, get_embedder
from product.rag.chunking import chunk_text
from product.rag.search import cosine, search_chunks, SearchHit

__all__ = [
    "Embedder", "FakeEmbedder", "GeminiEmbedder", "get_embedder",
    "chunk_text", "cosine", "search_chunks", "SearchHit",
]
