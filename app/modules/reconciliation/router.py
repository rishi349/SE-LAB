from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, get_db, rate_limit_by_user, require_admin
from app.core.ids import RUN_ID_PATTERN
from app.core.schemas import ERROR_RESPONSES, ErrorResponse
from app.modules.reconciliation import service
from app.modules.reconciliation.schemas import RunPage, RunReportOut

router = APIRouter(
    prefix="/admin/reconciliation-runs",
    tags=["Reconciliation"],
    responses=ERROR_RESPONSES,
    dependencies=[Depends(require_admin)],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=RunReportOut,
    dependencies=[Depends(rate_limit_by_user("reconciliation"))],
    summary="Run reconciliation now (read-only; never repairs data)",
)
def trigger_run(
    admin: CurrentUser = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.run_reconciliation(conn, triggered_by=admin.user_id)


@router.get("", response_model=RunPage, summary="Previous reconciliation runs (newest first)")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.list_runs(conn, page=page, page_size=page_size)


@router.get(
    "/{run_id}",
    response_model=RunReportOut,
    responses={404: {"model": ErrorResponse}},
    summary="One reconciliation report with its discrepancies",
)
def get_run(
    run_id: str = Path(pattern=RUN_ID_PATTERN),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.get_report(conn, run_id)
