"""
Компании и пользователи: регистрация, вход, выдача доступов.

Это «административный» слой над auth-примитивами:
  * register_company — самообслуживание: создаёт компанию и её первого
    пользователя-собственника (owner) одним действием;
  * create_user — owner заводит управляющих и сотрудников (в своей компании,
    опционально привязывая к точке);
  * authenticate — проверка email+пароля в рамках компании.

Везде — изоляция тенанта и уникальность email внутри компании.
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from product.auth import ROLE_OWNER, ROLES
from product.auth.security import hash_password, verify_password
from product.db import models as m


class AccountError(Exception):
    """Доменная ошибка аккаунтов (дубликат email, неизвестная роль и т.п.)."""


def _find_user(db: Session, company_id: str, email: str) -> Optional[m.User]:
    return db.execute(
        select(m.User).where(
            m.User.company_id == company_id,
            m.User.email == email.lower(),
        )
    ).scalars().first()


def register_company(
    db: Session, *, company_name: str, slug: str,
    owner_email: str, owner_password: str, owner_name: str = "",
) -> Tuple[m.Company, m.User]:
    """Создать компанию и её владельца. Падает, если slug уже занят."""
    exists = db.execute(select(m.Company).where(m.Company.slug == slug)).scalars().first()
    if exists:
        raise AccountError("Компания с таким slug уже существует")

    company = m.Company(slug=slug, name=company_name)
    db.add(company)
    db.flush()

    owner = m.User(
        company_id=company.id, email=owner_email.lower(),
        password_hash=hash_password(owner_password),
        full_name=owner_name, role=ROLE_OWNER,
    )
    db.add(owner)
    db.commit()
    db.refresh(company)
    db.refresh(owner)
    return company, owner


def create_user(
    db: Session, company_id: str, *,
    email: str, password: str, role: str,
    full_name: str = "", point_id: Optional[str] = None,
) -> m.User:
    """Завести пользователя в компании. role ∈ {owner, manager, employee}."""
    if role not in ROLES:
        raise AccountError(f"Неизвестная роль: {role!r}")
    if _find_user(db, company_id, email):
        raise AccountError("Пользователь с таким email уже есть в компании")

    user = m.User(
        company_id=company_id, email=email.lower(),
        password_hash=hash_password(password), full_name=full_name,
        role=role, point_id=point_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, *, slug: str, email: str, password: str) -> m.User:
    """Проверить вход по компании (slug) + email + пароль. Бросает AccountError."""
    company = db.execute(select(m.Company).where(m.Company.slug == slug)).scalars().first()
    if not company:
        raise AccountError("Неверные учётные данные")
    user = _find_user(db, company.id, email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AccountError("Неверные учётные данные")
    return user
