"""Тесты «Сводки и тревог» (M7).

Главное, что проверяем БЕЗ сети/модели:
  * тревоги считаются ДЕТЕРМИНИРОВАННО из цифр (значит, не галлюцинируют);
  * проблемная точка (bad) поднимает тревоги, хорошая (good) — нет;
  * сводка собирается офлайн (запасной текст без модели);
  * ранжирование ставит проседающую точку выше хорошей.
"""

from product.modules import accounts, digest, reviews as reviews_mod
from product.reviews.source import FakeReviewSource


def _company(db):
    company, owner = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()
    return company


_FIRM = {"b-": "70000001000000001", "g-": "70000001000000002"}


def _add_point(db, company_id, name, profile, prefix):
    p = reviews_mod.connect_point(db, company_id, name=name,
                                  url=f"https://2gis.kz/almaty/firm/{_FIRM[prefix]}")
    db.commit()
    reviews_mod.sync_reviews(db, company_id, p.id,
                             source=FakeReviewSource(profile=profile, prefix=prefix))
    # Разбор без живой модели → откат к оценке (rating).
    reviews_mod.analyze_pending(db, company_id, point_id=p.id,
                                llm=lambda *a, **k: "{}")
    return p


def test_compute_alerts_flags_bad_point(db):
    company = _company(db)
    _add_point(db, company.id, "Зал на Сатпаева", "bad", "b-")
    cc = reviews_mod.command_center(db, company.id)
    alerts = digest.compute_alerts(cc)
    assert alerts, "плохая точка должна поднять хотя бы одну тревогу"
    # Есть тревога высокой важности и она про нашу точку.
    assert any(a["severity"] == "high" for a in alerts)
    assert any("Сатпаева" in a["message"] for a in alerts)


def test_good_point_has_no_high_alerts(db):
    company = _company(db)
    _add_point(db, company.id, "Зал на Достык", "good", "g-")
    cc = reviews_mod.command_center(db, company.id)
    alerts = digest.compute_alerts(cc)
    assert not any(a["severity"] == "high" for a in alerts)


def test_build_digest_offline(db):
    company = _company(db)
    _add_point(db, company.id, "Зал на Сатпаева", "bad", "b-")
    _add_point(db, company.id, "Зал на Достык", "good", "g-")
    # Без llm → детерминированный запасной текст; цифры из данных.
    d = digest.build_digest(db, company.id, llm=lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    assert d["has_data"] is True
    assert d["summary"]  # текст собрался
    assert d["pulse"]["total"] > 0
    # Ранжирование: проседающая точка — первой.
    assert d["points"][0]["name"] == "Зал на Сатпаева"
    assert d["alerts"]


def test_build_digest_empty(db):
    company = _company(db)
    d = digest.build_digest(db, company.id)
    assert d["has_data"] is False
    assert "нет данных" in d["summary"].lower()
    assert d["alerts"] == []
