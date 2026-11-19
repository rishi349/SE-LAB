from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.validators import check_new_password, normalize_email, normalize_name
from app.modules.users.schemas import ProfileOut
from app.modules.wallets.schemas import WalletOut


class RegisterRequest(BaseModel):
    # extra="forbid": a client cannot smuggle in "role": "admin" or a chosen user_id.
    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=200, examples=["Asha Rao"])
    email: str = Field(max_length=254, examples=["asha@example.com"])
    password: str = Field(max_length=256, examples=["a-strong-password"])

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return check_new_password(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class RegisterResponse(BaseModel):
    user: ProfileOut
    wallet: WalletOut


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_in: int
