"""Small input normalisers shared by request schemas and services."""

from __future__ import annotations

import re

from app.core.security import BCRYPT_MAX_BYTES

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{8,128}$")
NAME_MAX_LENGTH = 100
PASSWORD_MIN_LENGTH = 8


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("must be a valid email address")
    return email


def normalize_name(value: str) -> str:
    name = " ".join(value.split())  # trim and collapse internal whitespace
    if not 1 <= len(name) <= NAME_MAX_LENGTH:
        raise ValueError(f"must be between 1 and {NAME_MAX_LENGTH} characters")
    if any(ord(ch) < 32 for ch in name):
        raise ValueError("must not contain control characters")
    return name


def check_new_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"must be at least {PASSWORD_MIN_LENGTH} characters")
    if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"must be at most {BCRYPT_MAX_BYTES} bytes")
    return value


def normalize_user_id(value: str) -> str:
    return value.strip().upper()
