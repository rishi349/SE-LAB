from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.core.schemas import Pagination

RunStatus = Literal["COMPLETED_CLEAN", "COMPLETED_WITH_DISCREPANCIES", "FAILED"]


class DiscrepancyOut(BaseModel):
    check_name: str
    entity_type: str
    entity_id: str
    expected: str | None
    actual: str | None
    detail: str


class RunSummaryOut(BaseModel):
    run_id: str
    status: RunStatus
    triggered_by: str
    started_at: str
    completed_at: str
    wallets_checked: int
    transactions_checked: int
    discrepancy_count: int
    failure_detail: str | None


class RunReportOut(RunSummaryOut):
    discrepancies: list[DiscrepancyOut]


class RunPage(BaseModel):
    items: list[RunSummaryOut]
    pagination: Pagination
