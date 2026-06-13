"""M9 — «Отслеживание исправлений»: руки цифрового опер-дира.

Петля: нашли проблему (в Сводке/Командном центре) → ПОРУЧИЛИ управляющему точки
→ ПРОВЕРИЛИ, что закрыто. Без этой петли продукт лишь «жалуется», а не доводит
до результата.

Модель простая и честная: задача (ActionItem) со статусом open → in_progress →
done, привязанная к точке (необязательно) и к источнику (откуда пришла: ручная,
тревога, боль клиентов, пробел в стандартах). Всё скоупится по company_id.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from product.agent_log import log_event
from product.db import models as m

VALID_STATUSES = (m.ACTION_OPEN, m.ACTION_IN_PROGRESS, m.ACTION_DONE)
VALID_SOURCES = ("manual", "alert", "problem", "gap")


class ActionError(Exception):
    """Некорректная операция с задачей (плохой статус, чужая точка и т.п.)."""


def create_action(db: Session, company_id: str, *, title: str,
                  detail: str = "", point_id: Optional[str] = None,
                  source: str = "manual", created_by: Optional[str] = None) -> m.ActionItem:
    """Поставить задачу на исправление. point_id — точка, если задача про филиал."""
    title = (title or "").strip()
    if not title:
        raise ActionError("Опишите, что нужно исправить.")
    if source not in VALID_SOURCES:
        source = "manual"
    if point_id is not None:  # проверяем, что точка наша
        point = db.get(m.Point, point_id)
        if point is None or point.company_id != company_id:
            raise ActionError("Точка не найдена")
    item = m.ActionItem(
        company_id=company_id, point_id=point_id, title=title[:512],
        detail=(detail or "").strip(), source=source, created_by=created_by)
    db.add(item)
    db.commit()
    db.refresh(item)
    log_event("actions.create", company=company_id, point=point_id,
              source=source, action=item.id)
    return item


def list_actions(db: Session, company_id: str, *, status: Optional[str] = None,
                 point_id: Optional[str] = None) -> List[m.ActionItem]:
    """Список задач компании. Открытые/в работе — раньше сделанных; новые сверху."""
    stmt = select(m.ActionItem).where(m.ActionItem.company_id == company_id)
    if status:
        stmt = stmt.where(m.ActionItem.status == status)
    if point_id:
        stmt = stmt.where(m.ActionItem.point_id == point_id)
    # done в конец, внутри группы — новые сверху.
    stmt = stmt.order_by(
        (m.ActionItem.status == m.ACTION_DONE).asc(),
        m.ActionItem.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def set_status(db: Session, company_id: str, action_id: str, status: str) -> m.ActionItem:
    """Сменить статус задачи (open|in_progress|done). done проставляет done_at."""
    if status not in VALID_STATUSES:
        raise ActionError(f"Недопустимый статус: {status}")
    item = db.get(m.ActionItem, action_id)
    if item is None or item.company_id != company_id:
        raise KeyError("Задача не найдена")
    item.status = status
    item.done_at = m._now() if status == m.ACTION_DONE else None
    db.commit()
    db.refresh(item)
    log_event("actions.status", company=company_id, action=action_id, status=status)
    return item


def delete_action(db: Session, company_id: str, action_id: str) -> bool:
    item = db.get(m.ActionItem, action_id)
    if item is None or item.company_id != company_id:
        raise KeyError("Задача не найдена")
    db.delete(item)
    db.commit()
    log_event("actions.delete", company=company_id, action=action_id)
    return True


def counts_by_status(db: Session, company_id: str) -> dict:
    """Сводка по статусам — для бейджей в интерфейсе."""
    rows = db.execute(
        select(m.ActionItem.status, func.count())
        .where(m.ActionItem.company_id == company_id)
        .group_by(m.ActionItem.status)).all()
    out = {m.ACTION_OPEN: 0, m.ACTION_IN_PROGRESS: 0, m.ACTION_DONE: 0}
    for status, n in rows:
        out[status] = n
    out["total"] = sum(out.values())
    out["active"] = out[m.ACTION_OPEN] + out[m.ACTION_IN_PROGRESS]
    return out
