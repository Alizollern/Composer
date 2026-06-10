"""
Шов 4 — реестр подключаемых инструментов.

Инструменты не зашиты в агента, а собираются loader'ом под каждого:
  - make_workspace_tools(): общая доска (обмен между агентами);
  - make_knowledge_tools(dir): личная база знаний агента (приватный RAG);
  - make_web_search(): реальный поиск (ddgs, без ключа) + чтение страниц.

Инструмент = {"schema": {...для модели...}, "fn": callable}.
"""

import re
import html
import urllib.request
from pathlib import Path

from composer.config import WORKSPACE

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def _safe(base, name):
    base = Path(base)
    p = (base / name).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise ValueError("Путь вне разрешённой папки запрещён")
    return p


# ---------- Общая доска (workspace) ----------
def make_workspace_tools():
    def write_file(path, content):
        p = _safe(WORKSPACE, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Записано {len(content)} символов в {path}"

    def read_file(path):
        p = _safe(WORKSPACE, path)
        return p.read_text() if p.exists() else f"Файл {path} не найден"

    def list_files(_=None):
        fs = [str(f.relative_to(WORKSPACE)) for f in WORKSPACE.rglob("*") if f.is_file()]
        return "\n".join(fs) if fs else "Рабочая папка пуста"

    return [
        {"schema": {"name": "write_file",
                    "description": "Записать текст в общий рабочий файл (виден другим агентам).",
                    "input_schema": {"type": "object", "properties": {
                        "path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"]}},
         "fn": lambda i: write_file(i["path"], i["content"])},
        {"schema": {"name": "read_file",
                    "description": "Прочитать общий рабочий файл.",
                    "input_schema": {"type": "object", "properties": {
                        "path": {"type": "string"}}, "required": ["path"]}},
         "fn": lambda i: read_file(i["path"])},
        {"schema": {"name": "list_files",
                    "description": "Список общих рабочих файлов.",
                    "input_schema": {"type": "object", "properties": {}}},
         "fn": lambda i: list_files()},
    ]


# ---------- Личная база знаний агента ----------
def make_knowledge_tools(knowledge_dir):
    kd = Path(knowledge_dir)
    kd.mkdir(parents=True, exist_ok=True)

    def list_knowledge(_=None):
        fs = [str(f.relative_to(kd)) for f in kd.rglob("*") if f.is_file()]
        return "\n".join(fs) if fs else "База знаний пуста"

    def read_knowledge(path):
        p = _safe(kd, path)
        return p.read_text() if p.exists() else f"В базе знаний нет {path}"

    def save_knowledge(path, content):
        p = _safe(kd, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Сохранено в базу знаний: {path}"

    return [
        {"schema": {"name": "list_knowledge",
                    "description": "Список файлов в собственной базе знаний агента.",
                    "input_schema": {"type": "object", "properties": {}}},
         "fn": lambda i: list_knowledge()},
        {"schema": {"name": "read_knowledge",
                    "description": "Прочитать файл из собственной базы знаний.",
                    "input_schema": {"type": "object", "properties": {
                        "path": {"type": "string"}}, "required": ["path"]}},
         "fn": lambda i: read_knowledge(i["path"])},
        {"schema": {"name": "save_knowledge",
                    "description": "Сохранить или обновить файл в собственной базе знаний.",
                    "input_schema": {"type": "object", "properties": {
                        "path": {"type": "string"}, "content": {"type": "string"}},
                        "required": ["path", "content"]}},
         "fn": lambda i: save_knowledge(i["path"], i["content"])},
    ]


# ---------- Веб-поиск + чтение страниц ----------
_SEARCH_BACKENDS = ["google", "bing", "brave", "yahoo", "duckduckgo"]


def _web_search(query, n=5):
    from ddgs import DDGS
    last_err = None
    for backend in _SEARCH_BACKENDS:
        try:
            results = DDGS().text(query, max_results=n, backend=backend)
        except Exception as e:
            last_err = e
            continue
        if results:
            return "\n\n".join(
                f"{i}. {r.get('title','')}\n   URL: {r.get('href','')}\n   {r.get('body','')}"
                for i, r in enumerate(results, 1))
    return f"Поиск не дал результатов (последняя ошибка: {last_err})."


def _fetch_url(url, max_chars=6000):
    req = urllib.request.Request(url, headers=_UA)
    raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    raw = re.sub(r"(?is)<(script|style|nav|footer|header).*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:max_chars] if text else "Страница пуста или недоступна."


def make_web_search():
    def web_search(query):
        try:
            return _web_search(query)
        except Exception as e:
            return f"Веб-поиск недоступен ({e}). Используй свои знания."

    def fetch_url(url):
        try:
            return _fetch_url(url)
        except Exception as e:
            return f"Не удалось открыть {url} ({e})."

    return [
        {"schema": {"name": "web_search",
                    "description": "Найти в интернете. Возвращает заголовки, URL и описания.",
                    "input_schema": {"type": "object", "properties": {
                        "query": {"type": "string"}}, "required": ["query"]}},
         "fn": lambda i: web_search(i["query"])},
        {"schema": {"name": "fetch_url",
                    "description": "Открыть страницу по URL и прочитать её текст (после web_search).",
                    "input_schema": {"type": "object", "properties": {
                        "url": {"type": "string"}}, "required": ["url"]}},
         "fn": lambda i: fetch_url(i["url"])},
    ]
