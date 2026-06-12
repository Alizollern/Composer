"""
RBAC-зависимости FastAPI: «кто звонит и что ему можно».

Здесь — единая точка авторизации продукта. Эндпоинт объявляет требование
(`Depends(require_owner)` и т.п.), а вся механика — разбор Bearer-токена,
поиск пользователя, проверка тенанта и роли — спрятана тут.

Изоляция тенантов: Principal несёт company_id из токена; репозитории/запросы
ОБЯЗАНЫ скоупиться по нему. Пользователь физически не может адресовать данные
чужой компании — id компании не приходит из тела запроса, только из токена.

Иерархия ролей: owner ⊃ manager ⊃ employee. require_manager пускает и owner;
require_employee пускает любого аутентифицированного.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from product.auth import ROLE_OWNER, ROLE_MANAGER, ROLE_EMPLOYEE
from product.auth.security import decode_access_token
from product.db import models as m
from product.db.session import get_session_factory

# Ранг роли: чем больше — тем шире права. Гард пускает роли с рангом >= требуемого.
_RANK = {ROLE_EMPLOYEE: 1, ROLE_MANAGER: 2, ROLE_OWNER: 3}

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    """Аутентифицированный вызывающий — результат проверки токена."""
    user_id: str
    company_id: str
    role: str
    point_id: Optional[str] = None

    def can(self, required_role: str) -> bool:
        return _RANK.get(self.role, 0) >= _RANK.get(required_role, 99)


def get_db() -> Iterator[Session]:
    """Сессия БД на время запроса; гарантированно закрывается."""
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def get_current_principal(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    """Достать и проверить токен → вернуть Principal. 401, если что-то не так."""
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    payload = decode_access_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен")

    user_id = payload.get("sub")
    company_id = payload.get("company_id")
    if not user_id or not company_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Повреждённый токен")

    # Сверяем с БД: пользователь существует, активен и принадлежит той же компании.
    user = db.get(m.User, user_id)
    if user is None or not user.is_active or user.company_id != company_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь недоступен")

    return Principal(
        user_id=user.id, company_id=user.company_id,
        role=user.role, point_id=user.point_id,
    )


def require_role(required_role: str) -> Callable[..., Principal]:
    """Фабрика гардов: вернуть зависимость, пускающую роль не ниже required_role."""

    def _guard(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.can(required_role):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return principal

    return _guard


# Готовые гарды для эндпоинтов.
require_owner = require_role(ROLE_OWNER)
require_manager = require_role(ROLE_MANAGER)
require_employee = require_role(ROLE_EMPLOYEE)
