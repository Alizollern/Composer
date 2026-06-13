"""Источники отзывов о точках сети (M4 — «цифровой опер-дир»).

Шов: продукт тянет отзывы через абстрактный ReviewSource, не зная, откуда они
берутся. Сегодня это парсер 2GIS; завтра — официальный API, Google/Yandex или
ручная загрузка. Меняется реализация за швом — бизнес-логика и хранение целы.
"""

from product.reviews.source import (
    ReviewSource, FakeReviewSource, TwoGisReviewSource,
    RawReview, get_review_source, parse_2gis_id,
)

__all__ = [
    "ReviewSource", "FakeReviewSource", "TwoGisReviewSource",
    "RawReview", "get_review_source", "parse_2gis_id",
]
