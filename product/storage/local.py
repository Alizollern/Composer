"""Локальное файловое хранилище (dev/тесты): объекты — это файлы в папке."""

from __future__ import annotations

from pathlib import Path

from product.storage.base import Storage


class LocalStorage(Storage):
    """Кладёт объекты в директорию root, повторяя структуру ключа как путь.

    Ключи строятся через build_key и не содержат `..`, поэтому выхода за пределы
    root быть не может; на всякий случай проверяем это явно.
    """

    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"Недопустимый ключ объекта: {key!r}")
        return p

    def put(self, key: str, data: bytes,
            *, content_type: str = "application/octet-stream") -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.is_file():
            raise KeyError(key)
        return p.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
