from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.money import SQLITE_MAX_INTEGER
from app.core.validators import normalize_user_id


class AdminUserOut(BaseModel):
    user_id: str
    name: str


class FundingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_user_id: str = Field(min_length=1, max_length=64)
    amount_paise: int = Field(
        strict=True,
        ge=-SQLITE_MAX_INTEGER,
        le=SQLITE_MAX_INTEGER,
        description="Amount in paise; must be positive. No upper cap.",
    )

    @field_validator("recipient_user_id")
    @classmethod
    def clean_recipient(cls, value: str) -> str:
        return normalize_user_id(value)
