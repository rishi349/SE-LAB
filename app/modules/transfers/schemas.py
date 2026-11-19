from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.money import SQLITE_MAX_INTEGER
from app.core.validators import normalize_user_id


class TransferRequest(BaseModel):
    """Amounts are integer paise. Floats and numeric strings are rejected (strict int).

    Zero or negative integers are *accepted by the schema* on purpose: they are recorded as
    failed transfer attempts, as required by the design.
    """

    model_config = ConfigDict(extra="forbid")

    recipient_user_id: str = Field(min_length=1, max_length=64, examples=["USR7K2M9Q4XAB"])
    amount_paise: int = Field(
        strict=True,
        ge=-SQLITE_MAX_INTEGER,
        le=SQLITE_MAX_INTEGER,
        examples=[150000],
        description="Amount in paise (₹1 = 100 paise).",
    )

    @field_validator("recipient_user_id")
    @classmethod
    def clean_recipient(cls, value: str) -> str:
        cleaned = normalize_user_id(value)
        if not cleaned:
            raise ValueError("must not be blank")
        return cleaned
