"""Password hashing (bcrypt) and JWT access tokens (HS256, 1 hour, no refresh tokens)."""

from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import jwt

from app.core.clock import utc_now
from app.core.errors import AuthenticationFailed

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_TTL = timedelta(hours=1)
BCRYPT_MAX_BYTES = 72

_dummy_hashes: dict[int, bytes] = {}


def hash_password(password: str, rounds: int) -> str:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("password exceeds bcrypt's 72-byte limit")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    raw = password.encode("utf-8")
    if password_hash is None or len(raw) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, password_hash.encode("utf-8"))
    except ValueError:
        return False


def burn_password_check(password: str, rounds: int) -> None:
    """Spend roughly the same time as a real check, so unknown emails are not detectable."""
    dummy = _dummy_hashes.get(rounds)
    if dummy is None:
        dummy = bcrypt.hashpw(b"timing-equaliser", bcrypt.gensalt(rounds))
        _dummy_hashes[rounds] = dummy
    raw = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    bcrypt.checkpw(raw, dummy)


def create_access_token(user_id: str, role: str, secret: str, now: datetime | None = None) -> str:
    issued = now or utc_now()
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": int(issued.timestamp()),
        "exp": int((issued + ACCESS_TOKEN_TTL).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, secret: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthenticationFailed() from exc
    if claims.get("type") != "access" or not isinstance(claims.get("sub"), str):
        raise AuthenticationFailed()
    return claims
