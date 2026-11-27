from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.core.schemas import Pagination

NotificationType = Literal["TRANSFER_SENT", "TRANSFER_RECEIVED", "TRANSFER_FAILED", "WALLET_FUNDED"]


class NotificationOut(BaseModel):
    notification_id: int
    type: NotificationType
    message: str
    amount_paise: int
    transaction_id: str
    is_read: bool
    created_at: str
    read_at: str | None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    pagination: Pagination
    unread_count: int


class UnreadCountOut(BaseModel):
    unread_count: int


class MarkAllReadOut(BaseModel):
    updated: int
