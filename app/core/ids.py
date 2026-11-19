"""Random public identifiers (Crockford base32: no I, L, O, U to avoid misreading)."""

from __future__ import annotations

import re
import secrets

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

USER_ID_PATTERN = r"^USR[0-9A-HJKMNP-TV-Z]{10}$"
TRANSACTION_ID_PATTERN = r"^TXN[0-9A-HJKMNP-TV-Z]{16}$"
RUN_ID_PATTERN = r"^REC[0-9A-HJKMNP-TV-Z]{12}$"

_USER_ID_RE = re.compile(USER_ID_PATTERN)


def _random(length: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def new_user_id() -> str:
    return "USR" + _random(10)


def new_wallet_id() -> str:
    return "WAL" + _random(10)


def new_transaction_id() -> str:
    return "TXN" + _random(16)


def new_run_id() -> str:
    return "REC" + _random(12)


def looks_like_user_id(value: str) -> bool:
    return bool(_USER_ID_RE.match(value))
