"""Response models shared by several modules (also used for the OpenAPI docs)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PartyOut(BaseModel):
    user_id: str
    name: str | None


class TransactionOut(BaseModel):
    transaction_id: str
    type: Literal["TRANSFER", "ADMIN_FUNDING"]
    status: Literal["SUCCESS", "FAILED"]
    direction: Literal["INCOMING", "OUTGOING"]
    amount_paise: int
    amount: str
    currency: Literal["INR"] = "INR"
    sender: PartyOut
    recipient: PartyOut
    created_at: str


class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    403: {"model": ErrorResponse, "description": "Not allowed"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    429: {"model": ErrorResponse, "description": "Rate limited"},
}
