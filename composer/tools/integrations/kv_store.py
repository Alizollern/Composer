"""
Интеграция: общий key-value стор (персист на диск).

Простое долговременное состояние, которое переживает прогоны и доступно
всем агентам: счётчики, флаги, заметки, кэш конфигурации клиента и т.п.
"""

import json
import threading

from composer.config import KV_FILE
from composer.tools.base import integration

_lock = threading.Lock()


def _load():
    return json.loads(KV_FILE.read_text()) if KV_FILE.exists() else {}


def _save(data):
    KV_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@integration(
    name="kv_set",
    description="Сохранить значение по ключу в общем хранилище (переживает прогоны).",
    input_schema={"type": "object",
                  "properties": {"key": {"type": "string"},
                                 "value": {"type": "string"}},
                  "required": ["key", "value"]},
    category="state",
)
def kv_set(inp):
    with _lock:
        data = _load()
        data[inp["key"]] = inp["value"]
        _save(data)
    return f"Сохранено: {inp['key']}"


@integration(
    name="kv_get",
    description="Прочитать значение по ключу из общего хранилища.",
    input_schema={"type": "object",
                  "properties": {"key": {"type": "string"}},
                  "required": ["key"]},
    category="state",
)
def kv_get(inp):
    with _lock:
        data = _load()
    return data.get(inp["key"], f"(ключ «{inp['key']}» не найден)")
