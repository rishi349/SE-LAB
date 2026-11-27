from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Path, Query

from app.core.deps import CurrentUser, get_current_user, get_db
from app.core.schemas import ERROR_RESPONSES, ErrorResponse
from app.modules.notifications import service
from app.modules.notifications.schemas import (
    MarkAllReadOut,
    NotificationOut,
    NotificationPage,
    UnreadCountOut,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"], responses=ERROR_RESPONSES)


@router.get("", response_model=NotificationPage, summary="My notifications (newest first)")
def list_my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(service.DEFAULT_PAGE_SIZE, ge=1, le=service.MAX_PAGE_SIZE),
    unread_only: bool = Query(False),
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.list_notifications(
        conn, user.user_id, page=page, page_size=page_size, unread_only=unread_only
    )


@router.get(
    "/unread-count", response_model=UnreadCountOut, summary="Number of unread notifications"
)
def my_unread_count(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return {"unread_count": service.unread_count(conn, user.user_id)}


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationOut,
    responses={404: {"model": ErrorResponse}},
    summary="Mark one of my notifications as read",
)
def mark_notification_read(
    notification_id: int = Path(ge=1),
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return service.mark_read(conn, user.user_id, notification_id)


@router.post("/read-all", response_model=MarkAllReadOut, summary="Mark all my notifications read")
def mark_all_my_notifications_read(
    user: CurrentUser = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return {"updated": service.mark_all_read(conn, user.user_id)}
