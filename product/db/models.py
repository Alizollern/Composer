"""
Схема данных Evergreen (SQLAlchemy 2.0, типизированный mapped-стиль).

Источник правды всего продукта. Ключевые принципы:

  * Мультитенантность. Почти каждая таблица несёт company_id — данные компаний
    строго изолированы (ТЗ §5 NFR). Запросы всегда скоупятся по company_id;
    репозитории/зависимости API обязаны это гарантировать.
  * Версионирование стандартов. Документ (Document) — это «карточка» стандарта;
    его текст живёт в версиях (DocumentVersion). Загрузили новую редакцию —
    появилась новая версия, старая остаётся в истории. RAG ищет по чанкам только
    текущей опубликованной версии.
  * RAG-чанки. Текст версии режется на чанки (Chunk), у каждого — эмбеддинг.
    Эмбеддинг хранится как JSON-массив float (переносимо между SQLite и
    Postgres). В проде поверх этого встаёт pgvector-индекс — это отдельный шов,
    модель данных при переезде не меняется.
  * «Вопросы без ответа» (QAGap). Если бот не нашёл ответ в базе знаний —
    он не выдумывает, а честно отказывает и логирует пробел сюда. Это и есть
    «карта незнания» для собственника (ТЗ: выявление пробелов в стандартах).

Портируемость: типы выбраны так, чтобы одна и та же схема поднималась и на
SQLite (офлайн-разработка и тесты), и на PostgreSQL (прод). Поэтому — generic
JSON, а не JSONB; UUID-строки, а не нативный pg-UUID.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship,
)

from product.auth import ROLE_EMPLOYEE


def _uuid() -> str:
    """Строковый UUID — первичный ключ, переносимый между SQLite и Postgres."""
    return uuid.uuid4().hex


def _now() -> datetime:
    """Текущее время в UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Базовый класс моделей. Generic JSON работает и на SQLite, и на Postgres."""
    type_annotation_map = {dict: JSON, list: JSON}


# Статусы документа: черновик → опубликован → в архиве.
DOC_DRAFT = "draft"
DOC_PUBLISHED = "published"
DOC_ARCHIVED = "archived"

# Статусы учебного трека (повторяют логику документа).
TRACK_DRAFT = "draft"
TRACK_PUBLISHED = "published"
TRACK_ARCHIVED = "archived"

# Статусы зачисления сотрудника на трек и прохождения отдельного шага.
ENROLL_ACTIVE = "active"
ENROLL_COMPLETED = "completed"
STEP_PENDING = "pending"
STEP_PASSED = "passed"


class Company(Base):
    """Тенант. Корень изоляции данных: всё остальное ссылается на company_id."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    users: Mapped[List["User"]] = relationship(back_populates="company")
    points: Mapped[List["Point"]] = relationship(back_populates="company")
    documents: Mapped[List["Document"]] = relationship(back_populates="company")


class Point(Base):
    """Точка (филиал) сети: кофейня/зал/ресторан. Сотрудник привязан к точке."""

    __tablename__ = "points"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(512), default="")
    # Привязка к внешнему источнику отзывов (цифровой опер-дир, M4).
    #   source       — "2gis" | "" (откуда тянем отзывы точки);
    #   external_id  — id филиала во внешнем источнике (для запроса отзывов);
    #   external_url — ссылка, которую владелец вставил (для удобства/повтора).
    source: Mapped[str] = mapped_column(String(32), default="")
    external_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    external_url: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    company: Mapped[Company] = relationship(back_populates="points")
    users: Mapped[List["User"]] = relationship(back_populates="point")


class User(Base):
    """Пользователь с ролью (owner|manager|employee). Пароль хранится только хешем."""

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("company_id", "email", name="uq_user_company_email"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    point_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("points.id", ondelete="SET NULL"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(32), default=ROLE_EMPLOYEE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    company: Mapped[Company] = relationship(back_populates="users")
    point: Mapped[Optional["Point"]] = relationship(back_populates="users")


class Document(Base):
    """Карточка стандарта. Сам текст — в версиях (DocumentVersion)."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    category: Mapped[str] = mapped_column(String(128), default="", index=True)
    status: Mapped[str] = mapped_column(String(32), default=DOC_DRAFT, index=True)
    # Аудитория стандарта (M1.5): кому он адресован.
    #   audience_roles — список ролей (["employee","manager"]). Пусто → всем ролям.
    #   point_id       — конкретная точка. NULL → всем точкам компании.
    # Сотрудник видит стандарт (в списке и в ответах бота), только если он входит
    # в его аудиторию; управляющий/собственник видят всё (управляют базой знаний).
    audience_roles: Mapped[list] = mapped_column(JSON, default=list)
    point_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("points.id", ondelete="SET NULL"), nullable=True, index=True)
    # Указатель на текущую (актуальную) версию. RAG индексирует именно её.
    current_version_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now)

    company: Mapped[Company] = relationship(back_populates="documents")
    versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    """Конкретная редакция стандарта. Новая загрузка → новая версия, старые живут."""

    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_no", name="uq_version_doc_no"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    content: Mapped[str] = mapped_column(Text)
    source_filename: Mapped[str] = mapped_column(String(512), default="")
    # Ключ оригинала в файловом хранилище (Storage). Пусто — если документ
    # создан из готового текста, без загрузки файла.
    source_uri: Mapped[str] = mapped_column(String(1024), default="")
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped[Document] = relationship(back_populates="versions")
    chunks: Mapped[List["Chunk"]] = relationship(
        back_populates="version", cascade="all, delete-orphan")


class Chunk(Base):
    """Фрагмент текста версии + его эмбеддинг. Единица поиска в RAG.

    embedding — JSON-массив float. На SQLite это TEXT, на Postgres — JSON;
    cosine считается в Python. Прод-оптимизация (pgvector + ANN-индекс) —
    отдельный шов в rag/, который подменяет способ поиска, не трогая схему.
    """

    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    version_id: Mapped[str] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list] = mapped_column(JSON, default=list)

    version: Mapped[DocumentVersion] = relationship(back_populates="chunks")


class QAGap(Base):
    """«Вопрос без ответа»: бот не нашёл ответ в базе знаний.

    Не выдумываем — фиксируем пробел. Для собственника это карта того, чего
    не хватает в стандартах (ТЗ: выявление пробелов / эскалация)."""

    __tablename__ = "qa_gaps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    # Лучшее, что нашёл поиск (для диагностики «почему не хватило»).
    best_score: Mapped[float] = mapped_column(default=0.0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Track(Base):
    """Учебный трек (онбординг): упорядоченный набор шагов-стандартов для роли.

    Собственник/управляющий собирает трек из документов; сотрудник проходит шаги
    по порядку, тест на каждом шаге гейтит переход. Это M3 «обучение и адаптация»."""

    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), default=TRACK_DRAFT, index=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now)

    steps: Mapped[List["TrackStep"]] = relationship(
        back_populates="track", cascade="all, delete-orphan",
        order_by="TrackStep.ordinal")


class TrackStep(Base):
    """Шаг трека: один стандарт + (опц.) проверочный тест с порогом сдачи."""

    __tablename__ = "track_steps"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str] = mapped_column(String(512), default="")
    require_quiz: Mapped[bool] = mapped_column(Boolean, default=True)
    pass_score: Mapped[float] = mapped_column(default=0.8)
    num_questions: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    track: Mapped[Track] = relationship(back_populates="steps")


class Enrollment(Base):
    """Зачисление сотрудника на трек. Прогресс по шагам — в StepProgress."""

    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("track_id", "user_id", name="uq_enrollment_track_user"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    track_id: Mapped[str] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=ENROLL_ACTIVE, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)


class StepProgress(Base):
    """Прогресс сотрудника по конкретному шагу трека (попытки, балл, статус)."""

    __tablename__ = "step_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "step_id", name="uq_progress_enrollment_step"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True)
    step_id: Mapped[str] = mapped_column(
        ForeignKey("track_steps.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=STEP_PENDING)
    score: Mapped[float] = mapped_column(default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now)


class QuizInstance(Base):
    """Сгенерированный тест, сохранённый на сервере.

    Вопросы вместе с верными ответами (correct_index) и цитатами (source_quote)
    живут ТОЛЬКО здесь. Клиенту при выдаче теста отдаются вопросы без этих полей,
    а при сдаче сервер грейдит ответы против этой серверной копии — поэтому
    правильные ответы не покидают бэкенд до момента проверки (нельзя подсмотреть).
    """

    __tablename__ = "quiz_instances"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    # Полный список вопросов: [{question, options, correct_index, source_quote}].
    questions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Источники отзывов и тональность (M4 — «цифровой опер-дир»).
REVIEW_2GIS = "2gis"
SENTIMENT_POSITIVE = "positive"
SENTIMENT_NEUTRAL = "neutral"
SENTIMENT_NEGATIVE = "negative"


class Review(Base):
    """Отзыв клиента о точке сети (из 2GIS и др.) + результат AI-разбора.

    Это «уши» цифрового опер-дира: система читает, что клиенты пишут о точке, и
    сопоставляет жалобы с внутренними стандартами — где реальность расходится с
    регламентом. Разбор хранится прямо в строке отзыва (денормализованно) — так
    проще и быстрее строить командный центр собственника.

    Поля разбора заполняются позже (analyzed=False → True): тональность, тема,
    признак жалобы, привязанный стандарт (matched_document_*) и рекомендация.
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("company_id", "source", "external_id",
                         name="uq_review_company_source_ext"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    point_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("points.id", ondelete="SET NULL"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default=REVIEW_2GIS)
    # id отзыва во внешнем источнике — чтобы не дублировать при повторной синхронизации.
    external_id: Mapped[str] = mapped_column(String(128), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    rating: Mapped[int] = mapped_column(Integer, default=0)  # 1..5 (0 — неизвестно)
    text: Mapped[str] = mapped_column(Text, default="")
    dated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)  # когда отзыв оставлен в источнике
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # --- Результат AI-разбора ---
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sentiment: Mapped[str] = mapped_column(String(16), default="")
    topic: Mapped[str] = mapped_column(String(255), default="")
    is_complaint: Mapped[bool] = mapped_column(Boolean, default=False)
    # Стандарт, которого касается жалоба (если нашёлся релевантный).
    matched_document_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    matched_document_title: Mapped[str] = mapped_column(String(512), default="")
    matched_quote: Mapped[str] = mapped_column(Text, default="")
    recommendation: Mapped[str] = mapped_column(Text, default="")


class ChatMessage(Base):
    """История диалога сотрудника с ботом. sources — на какие чанки сослался ответ."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Статусы задачи на исправление: открыта → в работе → сделана.
ACTION_OPEN = "open"
ACTION_IN_PROGRESS = "in_progress"
ACTION_DONE = "done"


class ActionItem(Base):
    """Задача на исправление — петля «нашли проблему → поручили → проверили».

    Собственник (или опер-дир) превращает боль из Командного центра/Сводки в
    конкретное поручение управляющему точки и отслеживает, что оно реально
    закрыто. Это «руки» цифрового опер-дира: не только увидеть проблему, но и
    довести её до исправления.

    source — откуда пришла задача: "manual" | "alert" | "problem" | "gap" —
    чтобы видеть, что именно породило поручение."""

    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    point_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("points.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=ACTION_OPEN, index=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    created_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    done_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)


class Competitor(Base):
    """Конкурент рядом с точкой сети — «глаза» опер-дира на рынок.

    Живой опер-директор смотрит, кто работает по соседству, чем они лучше и где
    слабее, чтобы переманивать клиентов. Для каждой нашей точки храним соседние
    заведения (из каталога 2GIS и др.): рейтинг, число отзывов, расстояние, а
    также за что их хвалят (strengths) и ругают (weaknesses) — это карта, где у
    нас зона роста, а где преимущество.

    Данные приходят из источника за адаптером (CompetitorSource), как и отзывы.
    Дедуп по (company_id, point_id, external_id) — повторная синхронизация
    обновляет, а не плодит дубли."""

    __tablename__ = "competitors"
    __table_args__ = (
        UniqueConstraint("company_id", "point_id", "external_id",
                         name="uq_competitor_company_point_ext"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True)
    # Наша точка, рядом с которой стоит этот конкурент.
    point_id: Mapped[str] = mapped_column(
        ForeignKey("points.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(32), default=REVIEW_2GIS)
    external_id: Mapped[str] = mapped_column(String(128), default="")
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(512), default="")
    distance_m: Mapped[int] = mapped_column(Integer, default=0)  # 0 — неизвестно
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    reviews_count: Mapped[int] = mapped_column(Integer, default=0)
    # За что хвалят / ругают конкурента (списки коротких тем из их отзывов).
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now)
