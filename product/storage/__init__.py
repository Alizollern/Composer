"""
Файловое хранилище оригиналов загруженных документов (шов).

Зачем шов: в проде оригиналы (pdf/docx) лежат в S3-совместимом объектном
хранилище; локально и в тестах — в обычной папке. Код модулей про это не знает,
он работает с интерфейсом Storage. Подмена backend'а — это конфиг, а не правка
бизнес-логики (тот же приём, что с Embedder и LLM-провайдером).

Ключ объекта (key) детерминирован и неймспейснут по тенанту:
    companies/{company_id}/documents/{document_id}/v{version_no}/{filename}
— поэтому объекты компаний не пересекаются, а путь читаем.
"""

from product.storage.base import Storage, build_key
from product.storage.factory import get_storage

__all__ = ["Storage", "build_key", "get_storage"]
