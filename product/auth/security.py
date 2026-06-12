"""
Примитивы безопасности: хеширование паролей и JWT-токены.

Пароли никогда не хранятся в открытом виде — только хеш (pbkdf2_sha256:
чистый Python, без нативных зависимостей, одинаково работает в деве и в проде).
Токен доступа — подписанный JWT с company_id, ролью и сроком жизни; на каждом
запросе он проверяется, отсюда API узнаёт «кто это и что ему можно».
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from product.config import JWT_SECRET, JWT_TTL_HOURS

# pbkdf2_sha256 — без native-бэкенда (bcrypt в новых версиях конфликтует с passlib).
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

_ALGO = "HS256"


def hash_password(password: str) -> str:
    """Вернуть хеш пароля для хранения в БД."""
    return _pwd.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Сверить введённый пароль с хешем. False — если не совпало или хеш битый."""
    try:
        return _pwd.verify(password, password_hash)
    except Exception:
        return False


def create_access_token(
    *, user_id: str, company_id: str, role: str,
    ttl_hours: Optional[int] = None, point_id: Optional[str] = None,
) -> str:
    """Выпустить подписанный JWT. В payload — всё, что нужно для авторизации
    без похода в БД: subject (user_id), компания, роль, точка."""
    ttl = JWT_TTL_HOURS if ttl_hours is None else ttl_hours
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "point_id": point_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ttl)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=_ALGO)


def decode_access_token(token: str) -> Optional[dict]:
    """Проверить подпись и срок токена. Вернуть payload или None, если невалиден."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[_ALGO])
    except JWTError:
        return None
