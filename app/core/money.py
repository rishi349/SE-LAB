"""Money rules. Every amount in the system is an ``int`` number of paise (1 rupee = 100 paise)."""

from __future__ import annotations

PAISE_PER_RUPEE = 100

MAX_SINGLE_TRANSFER_PAISE = 50_000 * PAISE_PER_RUPEE  # ₹50,000
MAX_DAILY_OUTGOING_PAISE = 1_00_000 * PAISE_PER_RUPEE  # ₹1,00,000 per IST day

# Largest value an SQLite INTEGER column can hold. Used only as an overflow guard.
SQLITE_MAX_INTEGER = 2**63 - 1


def is_paise(value: object) -> bool:
    """True for real ints only (bool is an int subclass in Python and is rejected)."""
    return isinstance(value, int) and not isinstance(value, bool)


def format_rupees(paise: int) -> str:
    """Render paise as a rupee string with two decimals, e.g. 123456 -> '1234.56'."""
    if not is_paise(paise):
        raise TypeError("amount must be an integer number of paise")
    sign = "-" if paise < 0 else ""
    rupees, rem = divmod(abs(paise), PAISE_PER_RUPEE)
    return f"{sign}{rupees}.{rem:02d}"
