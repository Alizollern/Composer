"""
M1 — База знаний (ядро продукта, приоритет P0).

Жизненный цикл стандарта:
  ingest_text/ingest_file → документ + версия №1 + чанки с эмбеддингами →
  публикация → семантический поиск (для чат-бота M2) → загрузка новой
  редакции (add_version) → версия №2, чанки переиндексируются.

Принципы:
  * Версионирование. Документ — «карточка»; текст — в версиях. Старые версии
    хранятся (история), но в поиске участвует ТОЛЬКО текущая опубликованная.
    Поэтому чанки всегда отражают текущую версию: при новой редакции старые
    чанки документа удаляются и индексируются новые.
  * Изоляция тенанта. Любая операция скоупится по company_id; чужое недоступно.
  * Эмбеддер — внедряемая зависимость (по умолчанию из окружения). Тесты
    передают FakeEmbedder и работают офлайн.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from product.db import models as m
from product.rag import chunk_text, get_embedder
from product.rag.embedder import Embedder
from product.modules.extract import extract_text
from product.storage import Storage, build_key, get_storage


def audience_ok(audience_roles, doc_point_id, *, role: str, point_id) -> bool:
    """Виден ли документ пользователю с данной ролью и точкой (M1.5).

    Правило: подходит по роли (пустой список ролей = всем) И по точке (NULL у
    документа = всем точкам). Используется и для списка, и для ретривала бота."""
    roles = audience_roles or []
    if roles and role not in roles:
        return False
    if doc_point_id is not None and doc_point_id != point_id:
        return False
    return True


def visible_document_ids(db: Session, company_id: str, *,
                         role: str, point_id) -> set:
    """Множество id документов компании, видимых пользователю (role/point)."""
    rows = db.execute(
        select(m.Document.id, m.Document.audience_roles, m.Document.point_id)
        .where(m.Document.company_id == company_id)
    ).all()
    return {
        did for did, roles, pid in rows
        if audience_ok(roles, pid, role=role, point_id=point_id)
    }


def set_audience(db: Session, company_id: str, document_id: str, *,
                 audience_roles: Optional[List[str]] = None,
                 point_id: Optional[str] = None) -> m.Document:
    """Назначить аудиторию документа: роли и/или точку (M1.5)."""
    doc = _get_owned(db, company_id, document_id)
    if audience_roles is not None:
        doc.audience_roles = list(audience_roles)
    doc.point_id = point_id
    db.commit()
    db.refresh(doc)
    return doc


def _index_version(db: Session, version: m.DocumentVersion, embedder: Embedder) -> int:
    """Нарезать версию на чанки, посчитать эмбеддинги и сохранить. Вернуть число чанков.

    Перед индексацией удаляет прежние чанки документа — чтобы в поиске жила
    только актуальная версия (старый текст не «всплывал» в ответах бота)."""
    db.query(m.Chunk).filter(m.Chunk.document_id == version.document_id).delete()

    pieces = chunk_text(version.content)
    if not pieces:
        return 0
    vectors = embedder.embed(pieces)
    chunks: List[m.Chunk] = []
    for ordinal, (text, vec) in enumerate(zip(pieces, vectors)):
        chunk = m.Chunk(
            company_id=version.company_id,
            document_id=version.document_id,
            version_id=version.id,
            ordinal=ordinal,
            text=text,
            embedding=vec,
        )
        db.add(chunk)
        chunks.append(chunk)

    # На Postgres дублируем эмбеддинги в pgvector-колонку (для ANN-индекса).
    # На SQLite это no-op. Нужен flush, чтобы у чанков появились id.
    from product.rag import pgvector_index
    if pgvector_index.is_postgres(db):
        db.flush()
        pgvector_index.sync_vectors(db, [(c.id, c.embedding) for c in chunks])
    return len(pieces)


def _store_original(
    storage: Optional[Storage], version: m.DocumentVersion, data: Optional[bytes],
) -> None:
    """Сохранить оригинал файла в хранилище и записать ключ в version.source_uri.

    Без данных (документ из готового текста) — ничего не делаем."""
    if not data:
        return
    storage = storage or get_storage()
    key = build_key(
        version.company_id, version.document_id,
        version.version_no, version.source_filename or "file")
    version.source_uri = storage.put(key, data)


def ingest_text(
    db: Session,
    company_id: str,
    *,
    title: str,
    content: str,
    category: str = "",
    source_filename: str = "",
    original_data: Optional[bytes] = None,
    audience_roles: Optional[List[str]] = None,
    point_id: Optional[str] = None,
    created_by: Optional[str] = None,
    publish: bool = True,
    embedder: Optional[Embedder] = None,
    storage: Optional[Storage] = None,
) -> m.Document:
    """Создать документ из готового текста: версия №1, чанки, (опц.) публикация.

    Если передан original_data (байты загруженного файла) — оригинал кладётся
    в файловое хранилище, а ключ сохраняется в version.source_uri.
    audience_roles/point_id — аудитория стандарта (M1.5); по умолчанию виден всем."""
    embedder = embedder or get_embedder()

    doc = m.Document(
        company_id=company_id, title=title, category=category,
        status=m.DOC_PUBLISHED if publish else m.DOC_DRAFT, created_by=created_by,
        audience_roles=list(audience_roles) if audience_roles else [],
        point_id=point_id,
    )
    db.add(doc)
    db.flush()  # нужен doc.id

    version = m.DocumentVersion(
        company_id=company_id, document_id=doc.id, version_no=1,
        content=content, source_filename=source_filename, created_by=created_by,
    )
    db.add(version)
    db.flush()  # нужен version.id

    doc.current_version_id = version.id
    _store_original(storage, version, original_data)
    _index_version(db, version, embedder)
    db.commit()
    db.refresh(doc)
    return doc


def ingest_file(
    db: Session,
    company_id: str,
    *,
    filename: str,
    data: bytes,
    title: Optional[str] = None,
    category: str = "",
    created_by: Optional[str] = None,
    publish: bool = True,
    embedder: Optional[Embedder] = None,
    storage: Optional[Storage] = None,
) -> m.Document:
    """Извлечь текст из файла (txt/md/pdf/docx), сохранить оригинал и проиндексировать."""
    content = extract_text(filename, data)
    return ingest_text(
        db, company_id,
        title=title or filename, content=content, category=category,
        source_filename=filename, original_data=data, created_by=created_by,
        publish=publish, embedder=embedder, storage=storage,
    )


def add_version(
    db: Session,
    company_id: str,
    document_id: str,
    *,
    content: str,
    source_filename: str = "",
    original_data: Optional[bytes] = None,
    created_by: Optional[str] = None,
    embedder: Optional[Embedder] = None,
    storage: Optional[Storage] = None,
) -> m.DocumentVersion:
    """Загрузить новую редакцию документа: версия N+1, переиндексация чанков.

    Старые версии остаются в истории; current_version_id переключается на новую.
    """
    embedder = embedder or get_embedder()
    doc = _get_owned(db, company_id, document_id)

    last_no = db.execute(
        select(m.DocumentVersion.version_no)
        .where(m.DocumentVersion.document_id == document_id)
        .order_by(m.DocumentVersion.version_no.desc())
    ).scalars().first() or 0

    version = m.DocumentVersion(
        company_id=company_id, document_id=document_id, version_no=last_no + 1,
        content=content, source_filename=source_filename, created_by=created_by,
    )
    db.add(version)
    db.flush()

    doc.current_version_id = version.id
    _store_original(storage, version, original_data)
    _index_version(db, version, embedder)
    db.commit()
    db.refresh(version)
    return version


def _get_owned(db: Session, company_id: str, document_id: str) -> m.Document:
    """Достать документ, убедившись что он принадлежит компании (иначе KeyError)."""
    doc = db.get(m.Document, document_id)
    if doc is None or doc.company_id != company_id:
        raise KeyError("Документ не найден")
    return doc


def get_document(db: Session, company_id: str, document_id: str) -> m.Document:
    return _get_owned(db, company_id, document_id)


def get_original(
    db: Session, company_id: str, document_id: str,
    *, storage: Optional[Storage] = None,
) -> tuple:
    """Вернуть (filename, bytes) оригинала текущей версии документа.

    KeyError — если документа нет, у текущей версии нет оригинала, либо объект
    отсутствует в хранилище."""
    doc = _get_owned(db, company_id, document_id)
    version = db.get(m.DocumentVersion, doc.current_version_id) if doc.current_version_id else None
    if version is None or not version.source_uri:
        raise KeyError("У документа нет оригинала файла")
    storage = storage or get_storage()
    data = storage.get(version.source_uri)
    return version.source_filename or "document", data


def list_documents(
    db: Session, company_id: str, *,
    status: Optional[str] = None, category: Optional[str] = None,
    audience_role: Optional[str] = None, audience_point_id: Optional[str] = None,
    enforce_audience: bool = False,
) -> List[m.Document]:
    """Список документов компании (фильтры: статус/категория; опц. аудитория M1.5).

    enforce_audience=True (для сотрудника) оставляет только документы его аудитории
    по audience_role/audience_point_id; для управляющего/owner — выключено (видят всё)."""
    stmt = select(m.Document).where(m.Document.company_id == company_id)
    if status:
        stmt = stmt.where(m.Document.status == status)
    if category:
        stmt = stmt.where(m.Document.category == category)
    stmt = stmt.order_by(m.Document.updated_at.desc())
    docs = list(db.execute(stmt).scalars().all())
    if enforce_audience:
        docs = [d for d in docs
                if audience_ok(d.audience_roles, d.point_id,
                               role=audience_role, point_id=audience_point_id)]
    return docs


def set_status(db: Session, company_id: str, document_id: str, status: str) -> m.Document:
    """Сменить статус документа (draft|published|archived)."""
    if status not in (m.DOC_DRAFT, m.DOC_PUBLISHED, m.DOC_ARCHIVED):
        raise ValueError(f"Неизвестный статус: {status!r}")
    doc = _get_owned(db, company_id, document_id)
    doc.status = status
    db.commit()
    db.refresh(doc)
    return doc
