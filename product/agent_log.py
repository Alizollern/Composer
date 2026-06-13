"""
Журнал «мыслей» агента — чтобы руководитель мог КОНТРОЛИРОВАТЬ ИИ.

Каждый раз, когда Evergreen обращается к языковой модели (ответ чат-бота,
генерация теста, любая агентная работа), сюда пишется одна строка: что у модели
спросили (system + вход), что она ответила, сколько времени заняло и какой модуль
это вызвал. Так появляется ПОЛНЫЙ, человекочитаемый след: видно, на основании
чего бот ответил и почему отказал.

Формат — JSONL (по одной JSON-записи в строке): удобно и читать глазами, и
обрабатывать программой. Путь к файлу — env EVERGREEN_AGENT_LOG
(по умолчанию var/logs/agent.jsonl). Логирование можно выключить
EVERGREEN_AGENT_LOG_ENABLED=0.

Журнал НЕ влияет на работу продукта: любая ошибка записи проглатывается — лог
никогда не должен ронять ответ пользователю.
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOCK = threading.Lock()


def _enabled() -> bool:
    return os.environ.get("EVERGREEN_AGENT_LOG_ENABLED", "1").strip().lower() not in (
        "0", "false", "no", "")


def _log_path() -> Path:
    return Path(os.environ.get("EVERGREEN_AGENT_LOG", "var/logs/agent.jsonl"))


def _clip(text: Any, limit: int = 4000) -> Any:
    """Обрезаем очень длинные тексты, чтобы журнал не разрастался безгранично."""
    if not isinstance(text, str):
        return text
    if len(text) <= limit:
        return text
    return text[:limit] + f"… [+{len(text) - limit} симв.]"


def log_event(kind: str, **fields: Any) -> None:
    """Записать одно событие в журнал агента (JSONL). Никогда не бросает наружу."""
    if not _enabled():
        return
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        **{k: _clip(v) for k, v in fields.items()},
    }
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False)
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
    except Exception:
        # Журнал — вспомогательный. Его сбой не должен влиять на продукт.
        pass


def read_recent(limit: int = 200) -> list[dict]:
    """Прочитать последние записи журнала (для экрана «Журнал ассистента»).

    Возвращает список словарей, новые — первыми. Битые строки пропускаем.
    Никогда не бросает наружу: при отсутствии файла — пустой список."""
    path = _log_path()
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    if limit and limit > 0:
        lines = lines[-limit:]
    out: list[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    out.reverse()  # новые сверху
    return out


class log_call:
    """Контекст-менеджер: засекает время вызова LLM и пишет результат/ошибку.

    Использование:
        with log_call("chat.answer", operation="strict_rag", system=sys, prompt=p) as ev:
            text = llm(...)
            ev.set_output(text)
    """

    def __init__(self, kind: str, **fields: Any):
        self.kind = kind
        self.fields = fields
        self._start = 0.0
        self._output: Optional[Any] = None

    def __enter__(self) -> "log_call":
        self._start = time.monotonic()
        return self

    def set_output(self, output: Any) -> None:
        self._output = output

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed_ms = int((time.monotonic() - self._start) * 1000)
        fields = dict(self.fields)
        fields["elapsed_ms"] = elapsed_ms
        if exc is not None:
            fields["error"] = f"{exc_type.__name__}: {exc}"
        else:
            fields["output"] = self._output
        log_event(self.kind, **fields)
        return False  # не подавляем исключения
