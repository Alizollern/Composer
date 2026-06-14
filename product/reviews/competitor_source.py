"""Адаптеры источников КОНКУРЕНТОВ (заведения рядом с точкой).

По аналогии с отзывами (source.py): стабильный интерфейс CompetitorSource —
«найди конкурентов рядом с филиалом external_id». Реализации:
  * TwoGisCompetitorSource — ищет похожие заведения через каталог 2GIS
    (best-effort, серая зона — как и парсинг отзывов);
  * FakeCompetitorSource   — детерминированный набор для офлайн/демо/тестов.

Выбор — get_competitor_source(): EVERGREEN_COMPETITORS_SOURCE=fake|2gis
(по умолчанию 2gis при заданном ключе 2GIS, иначе fake — чтобы офлайн не падало).

ЧЕСТНО: каталог 2GIS — отдельный публичный API, тоже хрупкий и формально серая
зона. Сильные/слабые стороны конкурента в идеале считаются из ЕГО отзывов —
это дорого (лишние вызовы), поэтому в первой версии реальный источник отдаёт
рейтинг/число отзывов, а strengths/weaknesses заполняются по мере развития.
Для демо фейковый источник даёт всё сразу, чтобы экран был наполнен.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Protocol

from product.reviews.source import parse_2gis_id


@dataclass
class RawCompetitor:
    """Сырой конкурент из источника (до сохранения)."""
    external_id: str
    name: str
    rating: float = 0.0
    reviews_count: int = 0
    address: str = ""
    distance_m: int = 0
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)


class CompetitorSource(Protocol):
    name: str

    def find(self, external_id: str, *, limit: int = 10) -> List[RawCompetitor]:
        ...


# --- Демо/офлайн: фиксированные наборы конкурентов по «профилям» -------------
# Профиль описывает рыночную позицию НАШЕЙ точки:
#   "tough"   — рядом сильные конкуренты (наша точка проседает) → есть куда расти;
#   "leading" — конкуренты слабее (наша точка — лидер района);
#   "mixed"   — вперемешку.

_FAKE_TOUGH = [
    RawCompetitor("c_fitzone", "FitZone", 4.7, 1240, "300 м", 300,
                  strengths=["свежий ремонт и чистота", "новые тренажёры",
                             "вежливый ресепшен"],
                  weaknesses=["дорогой абонемент", "мало парковки"]),
    RawCompetitor("c_powerhouse", "PowerHouse Gym", 4.5, 860, "600 м", 600,
                  strengths=["просторный зал", "много групповых программ"],
                  weaknesses=["очереди в час пик"]),
    RawCompetitor("c_xfit", "X-Fit Express", 4.4, 540, "800 м", 800,
                  strengths=["удобное расписание", "есть бассейн"],
                  weaknesses=["высокая цена", "сложно записаться к тренеру"]),
]
_FAKE_LEADING = [
    RawCompetitor("c_oldschool", "Качалка на районе", 3.6, 210, "400 м", 400,
                  strengths=["низкая цена"],
                  weaknesses=["старое оборудование", "грязные раздевалки"]),
    RawCompetitor("c_gym24", "Gym 24", 3.9, 430, "700 м", 700,
                  strengths=["круглосуточно"],
                  weaknesses=["мало тренеров", "шумно и тесно"]),
]
_FAKE_MIXED = [
    RawCompetitor("c_fitlife", "FitLife", 4.1, 600, "350 м", 350,
                  strengths=["хорошие тренеры", "чисто"],
                  weaknesses=["дорого"]),
    RawCompetitor("c_budget", "Бюджет-Фитнес", 3.5, 180, "500 м", 500,
                  strengths=["самая низкая цена в районе"],
                  weaknesses=["старые тренажёры", "тесно"]),
]
_FAKE_PROFILES = {"tough": _FAKE_TOUGH, "leading": _FAKE_LEADING,
                  "mixed": _FAKE_MIXED}


class FakeCompetitorSource:
    """Источник без сети: фиксированные конкуренты (офлайн/тесты/демо).

    profile — рыночная позиция нашей точки (tough|leading|mixed). prefix —
    добавляется к external_id, чтобы конкуренты разных точек не считались
    дублями (дедуп по external_id внутри точки)."""

    name = "2gis"

    def __init__(self, profile: str = "mixed", prefix: str = ""):
        self.profile = profile
        self.prefix = prefix

    def find(self, external_id: str, *, limit: int = 10) -> List[RawCompetitor]:
        rows = _FAKE_PROFILES.get(self.profile, _FAKE_MIXED)
        out: List[RawCompetitor] = []
        for c in rows[:limit]:
            out.append(RawCompetitor(
                external_id=f"{self.prefix}{c.external_id}", name=c.name,
                rating=c.rating, reviews_count=c.reviews_count,
                address=c.address, distance_m=c.distance_m,
                strengths=list(c.strengths), weaknesses=list(c.weaknesses)))
        return out


class TwoGisCompetitorSource:
    """Ищет похожие заведения рядом через каталог 2GIS (best-effort).

    Берёт нашу карточку филиала, определяет рубрику и координаты, затем ищет
    заведения той же рубрики поблизости. strengths/weaknesses в первой версии
    не заполняются (нужны отзывы конкурента — дорого); отдаём рейтинг и число
    отзывов. Структура готова — когда появится официальный доступ, меняем только
    этот класс.
    """

    name = "2gis"
    _DEFAULT_KEY = "rurbbn3446"  # публичный ключ каталога 2GIS (может смениться)
    _BASE = "https://catalog.api.2gis.com/3.0/items"

    def __init__(self, key: Optional[str] = None, locale: str = "ru_KZ"):
        self.key = key or os.environ.get("EVERGREEN_2GIS_CATALOG_KEY",
                                         self._DEFAULT_KEY)
        self.locale = os.environ.get("EVERGREEN_2GIS_LOCALE", locale)

    def find(self, external_id: str, *, limit: int = 10) -> List[RawCompetitor]:
        import requests  # локальный импорт: офлайн/тесты не требуют сети

        branch = parse_2gis_id(external_id)
        # 1) Узнаём рубрику и координаты нашей точки.
        info = requests.get(self._BASE, params={
            "id": branch, "key": self.key, "locale": self.locale,
            "fields": "items.point,items.rubrics",
        }, timeout=20)
        info.raise_for_status()
        items = (info.json().get("result") or {}).get("items") or []
        if not items:
            return []
        me = items[0]
        point = me.get("point") or {}
        rubrics = me.get("rubrics") or []
        rubric_id = rubrics[0].get("id") if rubrics else None
        lon, lat = point.get("lon"), point.get("lat")
        if lon is None or lat is None:
            return []
        # 2) Ищем похожие заведения рядом.
        params = {
            "key": self.key, "locale": self.locale,
            "point": f"{lon},{lat}", "radius": 2000,
            "sort": "rating", "page_size": min(max(limit, 1), 20),
            "fields": ("items.point,items.reviews,items.address_name,"
                       "items.adm_div"),
        }
        if rubric_id:
            params["rubric_id"] = rubric_id
        resp = requests.get(self._BASE, params=params, timeout=20)
        resp.raise_for_status()
        rows = (resp.json().get("result") or {}).get("items") or []
        out: List[RawCompetitor] = []
        for r in rows:
            rid = str(r.get("id") or "")
            if not rid or rid == branch:
                continue  # себя пропускаем
            reviews = r.get("reviews") or {}
            out.append(RawCompetitor(
                external_id=rid,
                name=str(r.get("name") or "Конкурент"),
                rating=float(reviews.get("general_rating") or 0.0),
                reviews_count=int(reviews.get("general_review_count") or 0),
                address=str(r.get("address_name") or ""),
            ))
            if len(out) >= limit:
                break
        return out


def get_competitor_source(name: Optional[str] = None) -> CompetitorSource:
    """Выбрать источник конкурентов по env (как get_review_source).

    EVERGREEN_COMPETITORS_SOURCE=fake|2gis. По умолчанию: 2gis, если задан ключ
    2GIS (значит прод/живой прогон); иначе fake (офлайн/тесты)."""
    name = (name or os.environ.get("EVERGREEN_COMPETITORS_SOURCE", "")).strip().lower()
    if not name:
        name = "2gis" if os.environ.get("EVERGREEN_2GIS_KEY") else "fake"
    if name == "fake":
        return FakeCompetitorSource()
    return TwoGisCompetitorSource()
