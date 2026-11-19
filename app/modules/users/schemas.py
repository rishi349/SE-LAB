from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import normalize_name


class ProfileOut(BaseModel):
    user_id: str
    name: str
    email: str
    role: Literal["user", "admin"]
    created_at: str
    name_changed_at: str | None
    next_name_change_allowed_at: str | None


class UpdateProfileRequest(BaseModel):
    # Only the name is editable. Sending email / user_id / role is rejected (422).
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_name(value)


class AccountDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=256)


class AccountDeletionResponse(BaseModel):
    user_id: str
    status: Literal["DEACTIVATED"]
    deactivated_at: str
    personal_data_deletion_due_at: str


class UserLookupOut(BaseModel):
    user_id: str
    name: str
