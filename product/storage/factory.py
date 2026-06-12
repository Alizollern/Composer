"""
Выбор backend'а хранилища — это конфиг, а не код.

Правило выбора:
  * EVERGREEN_STORAGE_BACKEND=local|s3 — если задан явно, используем его;
  * иначе: если задан EVERGREEN_S3_ENDPOINT (или bucket+ключи) → s3, иначе local.

get_storage() кеширует один экземпляр на процесс.
"""

from __future__ import annotations

from typing import Optional

from product import config
from product.storage.base import Storage
from product.storage.local import LocalStorage

_instance: Optional[Storage] = None


def _build() -> Storage:
    backend = config.STORAGE_BACKEND.strip().lower()
    if not backend:
        backend = "s3" if config.S3_ENDPOINT else "local"

    if backend == "s3":
        from product.storage.s3 import S3Storage
        return S3Storage(
            endpoint=config.S3_ENDPOINT, bucket=config.S3_BUCKET,
            access_key=config.S3_ACCESS_KEY, secret_key=config.S3_SECRET_KEY,
            region=config.S3_REGION,
        )
    return LocalStorage(config.STORAGE_DIR)


def get_storage() -> Storage:
    global _instance
    if _instance is None:
        _instance = _build()
    return _instance
