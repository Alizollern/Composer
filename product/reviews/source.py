"""Адаптеры источников отзывов.

ReviewSource — стабильный интерфейс: «дай отзывы для филиала external_id».
Реализации:
  * TwoGisReviewSource — тянет отзывы из публичного reviews-API 2GIS;
  * FakeReviewSource   — фиксированный набор для офлайн-разработки и тестов.

Выбор реализации — get_review_source(), как и у эмбеддера: по env
EVERGREEN_REVIEWS_SOURCE=fake|2gis (по умолчанию 2gis, если задан ключ 2GIS,
иначе fake — чтобы офлайн ничего не падало по сети).

ВАЖНО (честно): парсинг 2GIS опирается на их внутренний публичный API и может
сломаться при изменениях на их стороне; формально это серая зона. Для первого
клиента/демо — ок, чтобы проверить ценность. Когда появится официальный доступ —
меняем только этот файл.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Protocol


@dataclass
class RawReview:
    """Сырой отзыв из источника (до AI-разбора и сохранения)."""
    external_id: str
    author: str
    rating: int            # 1..5 (0 — неизвестно)
    text: str
    dated_at: Optional[datetime] = None


class ReviewSource(Protocol):
    name: str

    def fetch(self, external_id: str, *, limit: int = 50) -> List[RawReview]:
        ...


# 2GIS-ссылки: id филиала — длинное число после /firm/ (иногда .../firm/<id>/<branch>).
_2GIS_ID_RE = re.compile(r"/firm/(\d+)(?:/(\d+))?")


def parse_2gis_id(url_or_id: str) -> str:
    """Извлечь id филиала 2GIS из ссылки (или вернуть как есть, если это число).

    Поддерживает форматы:
      https://2gis.kz/almaty/firm/70000001006012345
      https://2gis.kz/almaty/firm/70000001006012345/70000001006099999/tab/reviews
    Если в ссылке две цифры (firm/branch) — берём ВТОРУЮ (branch_id), т.к. отзывы
    в 2GIS привязаны к филиалу; если одна — её.
    """
    s = (url_or_id or "").strip()
    if s.isdigit():
        return s
    m = _2GIS_ID_RE.search(s)
    if not m:
        raise ValueError("Не удалось распознать id филиала в ссылке 2GIS")
    return m.group(2) or m.group(1)


class TwoGisReviewSource:
    """Тянет отзывы из публичного reviews-API 2GIS (best-effort)."""

    name = "2gis"
    # Публичный ключ, которым пользуется веб-виджет 2GIS. Может смениться —
    # тогда переопределить через env EVERGREEN_2GIS_KEY.
    _DEFAULT_KEY = "6e7e1929-4ea9-4a5d-8c05-d601860389bd"
    _BASE = "https://public-api.reviews.2gis.com/2.0/branches/{branch}/reviews"

    def __init__(self, key: Optional[str] = None, locale: str = "ru_KZ"):
        self.key = key or os.environ.get("EVERGREEN_2GIS_KEY", self._DEFAULT_KEY)
        self.locale = os.environ.get("EVERGREEN_2GIS_LOCALE", locale)

    def fetch(self, external_id: str, *, limit: int = 50) -> List[RawReview]:
        import requests  # локальный импорт: офлайн/тесты не требуют сети

        branch = parse_2gis_id(external_id)
        params = {
            "limit": min(max(limit, 1), 50),
            "is_advertiser": "false",
            "fields": "meta.providers,meta.branch_rating,meta.branch_reviews_count",
            "without_my_first_review": "false",
            "rated": "true",
            "sort_by": "date_created",
            "key": self.key,
            "locale": self.locale,
        }
        url = self._BASE.format(branch=branch)
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json() or {}
        out: List[RawReview] = []
        for r in (data.get("reviews") or []):
            out.append(RawReview(
                external_id=str(r.get("id") or ""),
                author=str((r.get("user") or {}).get("name") or "Гость"),
                rating=int(r.get("rating") or 0),
                text=str(r.get("text") or "").strip(),
                dated_at=_parse_dt(r.get("date_created")),
            ))
        return [r for r in out if r.text]


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    s = str(value).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --- Демо/офлайн: фиксированный набор «как из 2GIS» -------------------------

_FAKE_REVIEWS = [
    ("g1", "Айдана", 2, "Раздевалка грязная, в душе не убрано, по углам мусор. "
     "За такие деньги ожидала чистоту."),
    ("g2", "Марат", 1, "Записался на заморозку абонемента, на ресепшене сказали "
     "что задним числом нельзя и нагрубили. Неприятный осадок."),
    ("g3", "Динара", 5, "Отличный зал, тренеры внимательные, всё нравится!"),
    ("g4", "Ерлан", 2, "Тренажёр для жима сломан уже вторую неделю, никто не "
     "чинит, таблички даже нет."),
    ("g5", "Сауле", 3, "В целом нормально, но на звонки долго не отвечают, "
     "дозвониться невозможно."),
    ("g6", "Тимур", 5, "Хожу полгода, всё супер, рекомендую."),
    ("g7", "Жанна", 1, "Хамское обслуживание на стойке, спорили со мной при "
     "других клиентах. Так нельзя."),
    ("g8", "Болат", 4, "Хороший клуб, но тренажёры протирают редко, хотелось бы "
     "почаще."),
]


class FakeReviewSource:
    """Источник без сети: одинаковый набор отзывов (для офлайн/тестов/демо)."""

    name = "2gis"

    def fetch(self, external_id: str, *, limit: int = 50) -> List[RawReview]:
        base = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)
        out = []
        for i, (eid, author, rating, text) in enumerate(_FAKE_REVIEWS[:limit]):
            out.append(RawReview(external_id=eid, author=author, rating=rating,
                                 text=text, dated_at=base))
        return out


def get_review_source(name: Optional[str] = None) -> ReviewSource:
    """Выбрать источник отзывов по env (как get_embedder).

    EVERGREEN_REVIEWS_SOURCE=fake|2gis. По умолчанию: 2gis, если задан ключ 2GIS
    (EVERGREEN_2GIS_KEY) — значит прод/живой прогон; иначе fake (офлайн/тесты).
    """
    name = (name or os.environ.get("EVERGREEN_REVIEWS_SOURCE", "")).strip().lower()
    if not name:
        name = "2gis" if os.environ.get("EVERGREEN_2GIS_KEY") else "fake"
    if name == "fake":
        return FakeReviewSource()
    return TwoGisReviewSource()
