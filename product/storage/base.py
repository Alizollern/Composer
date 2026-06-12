"""Интерфейс хранилища и хелпер построения ключа."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug_filename(filename: str) -> str:
    """Обезопасить имя файла для использования в ключе/пути (без слешей и пробелов)."""
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].strip() or "file"
    return _SAFE.sub("_", name)


def build_key(company_id: str, document_id: str, version_no: int, filename: str) -> str:
    """Детерминированный ключ объекта, неймспейснутый по тенанту и версии."""
    return (
        f"companies/{company_id}/documents/{document_id}"
        f"/v{version_no}/{_slug_filename(filename)}"
    )


class Storage(ABC):
    """Минимальный контракт хранилища оригиналов: положить / достать / проверить."""

    @abstractmethod
    def put(self, key: str, data: bytes,
            *, content_type: str = "application/octet-stream") -> str:
        """Сохранить байты под ключом. Возвращает тот же key (идентификатор объекта)."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Прочитать объект по ключу. KeyError, если объекта нет."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Есть ли объект под ключом."""
