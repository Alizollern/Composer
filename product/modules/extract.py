"""
Извлечение текста из загруженных файлов (M1: приём стандартов).

Поддержка форматов, в которых обычно лежат регламенты:
  * .txt/.md           — как есть (utf-8, с запасным декодированием);
  * .pdf               — через pymupdf4llm (уже в зависимостях движка);
  * .docx              — разбором OOXML из zip (word/document.xml), без доп.
                         зависимостей: .docx — это zip с XML внутри.

Возвращаем плоский текст; разметку/таблицы упрощаем. Если формат неизвестен —
честно поднимаем ValueError, чтобы API отдал понятную ошибку, а не «тишину».
"""

from __future__ import annotations

import io
import re
import zipfile


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_docx(data: bytes) -> str:
    """Текст из .docx: читаем word/document.xml, склеиваем <w:t>, абзацы — по <w:p>."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # Границы абзацев и переводы строк сохраняем как \n.
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:br\s*/>", "\n", xml)
    # Вытаскиваем содержимое текстовых узлов <w:t>…</w:t>.
    parts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, flags=re.DOTALL)
    text = "".join(parts)
    # Снимаем оставшиеся теги и разэкранируем базовые сущности.
    text = re.sub(r"<[^>]+>", "", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<")
                .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    return text


def _extract_pdf(data: bytes) -> str:
    import pymupdf4llm
    import fitz  # pymupdf
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return pymupdf4llm.to_markdown(doc)
    finally:
        doc.close()


def extract_text(filename: str, data: bytes) -> str:
    """Достать текст из файла по его расширению. Поднимает ValueError на неизвестный тип."""
    name = (filename or "").lower()
    if name.endswith((".txt", ".md", ".markdown")):
        return _decode(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    raise ValueError(f"Неподдерживаемый формат файла: {filename!r}")
