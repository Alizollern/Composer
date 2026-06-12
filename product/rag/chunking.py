"""
Нарезка документа на чанки для RAG.

Длинный стандарт нельзя ни целиком засунуть в эмбеддинг, ни показать модели —
режем на куски ~по словам, с нахлёстом, чтобы мысль на стыке не терялась.
Режем по абзацам/предложениям, не разрывая слова. Размер — в «словах», а не
символах: грубо, но переносимо и без токенизатора.
"""

from __future__ import annotations

import re
from typing import List

_PARA_RE = re.compile(r"\n\s*\n")  # пустая строка — граница абзаца
_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def chunk_text(text: str, *, target_words: int = 180, overlap_words: int = 30) -> List[str]:
    """Разбить текст на чанки примерно по target_words слов с нахлёстом overlap_words.

    Сначала собираем абзацы, пока не наберём target_words; затем начинаем новый
    чанк, прихватывая хвост предыдущего (overlap) — чтобы граница не рвала контекст.
    """
    text = _normalize(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in _PARA_RE.split(text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0

    def flush():
        nonlocal cur, cur_len
        if cur:
            chunks.append(" ".join(cur).strip())
            cur, cur_len = [], 0

    for para in paragraphs:
        words = _WS_RE.split(para)
        # Абзац длиннее лимита — режем его по словам.
        if len(words) > target_words:
            flush()
            for i in range(0, len(words), target_words - overlap_words):
                piece = words[i:i + target_words]
                if piece:
                    chunks.append(" ".join(piece).strip())
            continue

        if cur_len + len(words) > target_words and cur:
            # Нахлёст: начинаем новый чанк с хвоста текущего.
            tail = " ".join(cur).split()[-overlap_words:] if overlap_words else []
            flush()
            cur = tail + words
            cur_len = len(cur)
        else:
            cur.extend(words)
            cur_len += len(words)

    flush()
    return [c for c in chunks if c]
