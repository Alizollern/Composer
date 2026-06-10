"""
Шов 3 — память.

Интерфейс важнее реализации: сегодня JSON-файл, завтра SAFLA / Cloudflare
Memory / векторная база — агент работает через read/write и не знает разницы.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path


class Memory(ABC):
    @abstractmethod
    def read(self, key): ...
    @abstractmethod
    def write(self, key, value): ...


class JSONMemory(Memory):
    def __init__(self, path):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, value):
        self.data[key] = value
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))


class InMemoryMemory(Memory):
    """Эфемерная память для одноразовых суб-прогонов (ничего не пишет на диск)."""

    def __init__(self):
        self.data = {}

    def read(self, key):
        return self.data.get(key)

    def write(self, key, value):
        self.data[key] = value
