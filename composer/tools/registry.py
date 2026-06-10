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
def make_workspace_tools(base=None):
    """base — корень рабочей папки. Для прогона в контексте компании сюда
    передаётся её папка (workspace/companies/<slug>/), и все чтения/записи
    скоупятся в неё. По умолчанию — общий WORKSPACE."""
    base = Path(base) if base else WORKSPACE
    base.mkdir(parents=True, exist_ok=True)

    def write_file(path, content):
        p = _safe(base, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Записано {len(content)} символов в {path}"

    def read_file(path):
        p = _safe(base, path)
        return p.read_text() if p.exists() else f"Файл {path} не найден"

    def list_files(_=None):
        fs = [str(f.relative_to(base)) for f in base.rglob("*")
              if f.is_file() and not f.name.startswith(".")]
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


# ---------- База знаний агента (приватная + общие домены) ----------
def make_knowledge_tools(roots):
    """roots: путь (приватная база) ИЛИ список (label, path).

    Первый корень — приватная база агента (туда пишет save_knowledge).
    Остальные — общие домены из корневого knowledge/ (только чтение).
    Файлы адресуются как "<label>/<путь>", напр. "Starbucks/look_book.md".
    """
    if isinstance(roots, (str, Path)):
        roots = [("self", Path(roots))]
    roots = [(label, Path(p)) for label, p in roots]
    # приватную базу создаём, общие — только если есть
    roots[0][1].mkdir(parents=True, exist_ok=True)

    def _iter():
        for label, base in roots:
            if not base.is_dir():
                continue
            for f in base.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".md", ".txt"):
                    yield label, base, f

    def _resolve(path):
        for label, base in roots:
            rel = path[len(label) + 1:] if path.startswith(label + "/") else path
            try:
                p = _safe(base, rel)
            except ValueError:
                continue
            if p.exists():
                return p
        return None

    def list_knowledge(_=None):
        fs = sorted(f"{label}/{f.relative_to(base)}" for label, base, f in _iter())
        return "\n".join(fs) if fs else "База знаний пуста"

    def read_knowledge(path, max_chars=15000):
        p = _resolve(path)
        if not p:
            return f"В базе знаний нет {path}"
        text = p.read_text(encoding="utf-8", errors="ignore")
        if len(text) > max_chars:
            return (text[:max_chars] +
                    f"\n\n…[обрезано: показано {max_chars} из {len(text)} символов. "
                    "Используй search_knowledge, чтобы найти нужный фрагмент в этом файле.]")
        return text

    def save_knowledge(path, content):
        base0 = roots[0][1]
        p = _safe(base0, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Сохранено в базу знаний: {path}"

    def search_knowledge(query, top=6):
        """Лёгкий поиск по всем доступным базам: ранжируем по совпадению слов,
        возвращаем имена + фрагменты. Агент не читает всё подряд (экономит токены)."""
        terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        if not terms:
            return "Уточни запрос (нужны слова длиннее 2 символов)."
        scored = []
        for label, base, f in _iter():
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            low = text.lower()
            score = sum(low.count(t) for t in terms)
            if score:
                pos = min((low.find(t) for t in terms if low.find(t) >= 0), default=0)
                snippet = text[max(0, pos - 120): pos + 280].replace("\n", " ").strip()
                scored.append((score, f"{label}/{f.relative_to(base)}", snippet))
        if not scored:
            return f"По запросу «{query}» в базе знаний ничего не найдено."
        scored.sort(reverse=True)
        return "\n\n".join(f"• {name} (совпадений: {score})\n  …{snippet}…"
                           for score, name, snippet in scored[:top])

    return [
        {"schema": {"name": "list_knowledge",
                    "description": "Список файлов в собственной базе знаний агента.",
                    "input_schema": {"type": "object", "properties": {}}},
         "fn": lambda i: list_knowledge()},
        {"schema": {"name": "search_knowledge",
                    "description": ("Найти в базе знаний релевантные документы по "
                                    "ключевым словам. Возвращает имена файлов и "
                                    "фрагменты. Используй ПЕРЕД read_knowledge, чтобы "
                                    "не читать всё подряд."),
                    "input_schema": {"type": "object", "properties": {
                        "query": {"type": "string"}}, "required": ["query"]}},
         "fn": lambda i: search_knowledge(i["query"])},
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


def _fetch_url(url, max_chars=2500):
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
