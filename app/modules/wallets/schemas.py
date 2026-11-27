from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WalletOut(BaseModel):
    wallet_id: str
    user_id: str
    balance_paise: int
    balance: str
    currency: Literal["INR"] = "INR"
    created_at: str
    updated_at: str
    unread_notifications: int = 0
