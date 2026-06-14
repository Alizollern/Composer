"""Тесты конкурентной разведки (экран «Конкуренты»).

Проверяем БЕЗ сети/модели:
  * синхронизация сохраняет конкурентов и дедуплицирует при повторе;
  * сравнение детерминированное: сильные соседи → статус «отстаём»,
    слабые → «лидируем»;
  * сборка экрана офлайн; точки, где проигрываем, идут выше.
"""

from product.db import models as m
from product.modules import accounts, competitors, reviews as reviews_mod
from product.reviews.source import FakeReviewSource
from product.reviews.competitor_source import FakeCompetitorSource


def _company(db):
    company, _ = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()
    return company


_FIRM = {"b-": "70000001000000001", "g-": "70000001000000002",
         "m-": "70000001000000003"}


def _add_point(db, company_id, name, profile, prefix):
    p = reviews_mod.connect_point(
        db, company_id, name=name,
        url=f"https://2gis.kz/almaty/firm/{_FIRM[prefix]}")
    db.commit()
    reviews_mod.sync_reviews(db, company_id, p.id,
                             source=FakeReviewSource(profile=profile, prefix=prefix))
    reviews_mod.analyze_pending(db, company_id, point_id=p.id,
                                llm=lambda *a, **k: "{}")
    return p


def test_sync_saves_and_dedupes(db):
    company = _company(db)
    p = _add_point(db, company.id, "Сатпаева", "bad", "b-")

    r1 = competitors.sync_competitors(
        db, company.id, p.id,
        source=FakeCompetitorSource(profile="tough", prefix="b-"))
    assert r1["added"] == 3
    # Повторная синхронизация не плодит дубли — обновляет.
    r2 = competitors.sync_competitors(
        db, company.id, p.id,
        source=FakeCompetitorSource(profile="tough", prefix="b-"))
    assert r2["added"] == 0
    assert r2["updated"] == 3


def test_tough_competitors_make_us_behind(db):
    company = _company(db)
    p = _add_point(db, company.id, "Сатпаева", "bad", "b-")
    competitors.sync_competitors(
        db, company.id, p.id,
        source=FakeCompetitorSource(profile="tough", prefix="b-"))

    view = competitors.build_view(db, company.id)
    block = view["points"][0]
    assert block["point_name"] == "Сатпаева"
    assert block["status"] in ("behind", "close")
    assert block["best_competitor_rating"] > block["my_rating"]
    # Сильные стороны соседей = наши зоны роста.
    assert block["opportunities"]


def test_leading_when_competitors_weaker(db):
    company = _company(db)
    p = _add_point(db, company.id, "Достык", "good", "g-")
    competitors.sync_competitors(
        db, company.id, p.id,
        source=FakeCompetitorSource(profile="leading", prefix="g-"))

    view = competitors.build_view(db, company.id)
    block = view["points"][0]
    assert block["status"] == "leading"
    assert block["ahead_of"] == block["competitors_count"]


def test_view_orders_behind_first(db):
    company = _company(db)
    bad = _add_point(db, company.id, "Сатпаева", "bad", "b-")
    good = _add_point(db, company.id, "Достык", "good", "g-")
    competitors.sync_competitors(
        db, company.id, bad.id,
        source=FakeCompetitorSource(profile="tough", prefix="b-"))
    competitors.sync_competitors(
        db, company.id, good.id,
        source=FakeCompetitorSource(profile="leading", prefix="g-"))

    view = competitors.build_view(db, company.id)
    assert view["has_data"] is True
    assert view["points"][0]["point_name"] == "Сатпаева"  # где горит — выше
    assert view["summary"]


def test_view_empty_without_sync(db):
    company = _company(db)
    _add_point(db, company.id, "Абая", "mixed", "m-")
    view = competitors.build_view(db, company.id)
    assert view["has_data"] is False


def test_sync_rejects_point_without_url(db):
    company = _company(db)
    # Точка без external_id (создана напрямую, без ссылки 2GIS).
    p = m.Point(company_id=company.id, name="Без ссылки", source="", external_id="")
    db.add(p)
    db.commit()
    db.refresh(p)
    try:
        competitors.sync_competitors(
            db, company.id, p.id, source=FakeCompetitorSource())
        assert False, "ожидали CompetitorError"
    except competitors.CompetitorError:
        pass
