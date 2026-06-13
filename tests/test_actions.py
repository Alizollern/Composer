"""Тесты «Отслеживания исправлений» (M9) — петля нашли → поручили → проверили."""

import pytest

from product.modules import accounts, actions, reviews as reviews_mod
from product.db import models as m


def _company(db):
    company, owner = accounts.register_company(
        db, company_name="Net", slug="net",
        owner_email="o@net.io", owner_password="secret1", owner_name="")
    db.commit()
    return company, owner


def test_create_and_list(db):
    company, owner = _company(db)
    a = actions.create_action(db, company.id, title="Протереть тренажёры",
                              detail="каждые 2 часа", created_by=owner.id)
    assert a.status == m.ACTION_OPEN
    items = actions.list_actions(db, company.id)
    assert len(items) == 1 and items[0].title == "Протереть тренажёры"


def test_status_flow_sets_done_at(db):
    company, owner = _company(db)
    a = actions.create_action(db, company.id, title="Починить кран")
    a = actions.set_status(db, company.id, a.id, m.ACTION_IN_PROGRESS)
    assert a.status == m.ACTION_IN_PROGRESS and a.done_at is None
    a = actions.set_status(db, company.id, a.id, m.ACTION_DONE)
    assert a.status == m.ACTION_DONE and a.done_at is not None
    # Возврат в работу обнуляет дату закрытия.
    a = actions.set_status(db, company.id, a.id, m.ACTION_OPEN)
    assert a.done_at is None


def test_bad_status_rejected(db):
    company, _ = _company(db)
    a = actions.create_action(db, company.id, title="x")
    with pytest.raises(actions.ActionError):
        actions.set_status(db, company.id, a.id, "wat")


def test_empty_title_rejected(db):
    company, _ = _company(db)
    with pytest.raises(actions.ActionError):
        actions.create_action(db, company.id, title="   ")


def test_point_scope_enforced(db):
    company, _ = _company(db)
    other, _ = accounts.register_company(
        db, company_name="Other", slug="other",
        owner_email="o@other.io", owner_password="secret1", owner_name="")
    db.commit()
    p = reviews_mod.connect_point(db, other.id, name="Чужая",
                                  url="https://2gis.kz/almaty/firm/70000001000000009")
    db.commit()
    # Нельзя повесить задачу на точку чужой компании.
    with pytest.raises(actions.ActionError):
        actions.create_action(db, company.id, title="x", point_id=p.id)


def test_counts_by_status(db):
    company, _ = _company(db)
    a1 = actions.create_action(db, company.id, title="a")
    actions.create_action(db, company.id, title="b")
    actions.set_status(db, company.id, a1.id, m.ACTION_DONE)
    c = actions.counts_by_status(db, company.id)
    assert c["total"] == 2 and c["done"] == 1 and c["active"] == 1


def test_done_sorted_last(db):
    company, _ = _company(db)
    a1 = actions.create_action(db, company.id, title="первая")
    a2 = actions.create_action(db, company.id, title="вторая")
    actions.set_status(db, company.id, a1.id, m.ACTION_DONE)
    items = actions.list_actions(db, company.id)
    assert items[-1].id == a1.id  # сделанная — в конце
