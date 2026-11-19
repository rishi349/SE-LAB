"""Time helpers. All stored timestamps are UTC strings; business days are IST days."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TS_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"  # fixed width, so string order == time order


def utc_now() -> datetime:
    return datetime.now(UTC)


def to_db(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return moment.astimezone(UTC).strftime(TS_FORMAT)


def from_db(value: str) -> datetime:
    return datetime.strptime(value, TS_FORMAT).replace(tzinfo=UTC)


def ist_day_window(moment: datetime) -> tuple[datetime, datetime]:
    """Return [start, end) in UTC of the IST calendar day containing ``moment``."""
    local_day = moment.astimezone(IST).date()
    start = datetime.combine(local_day, time.min, tzinfo=IST)
    end = start + timedelta(days=1)
    return start.astimezone(UTC), end.astimezone(UTC)


def ist_dates_to_utc_range(
    from_date: date | None, to_date: date | None
) -> tuple[str | None, str | None]:
    """Convert inclusive IST calendar dates into a [start, end) UTC string range."""
    start = end = None
    if from_date is not None:
        start = to_db(datetime.combine(from_date, time.min, tzinfo=IST))
    if to_date is not None:
        end = to_db(datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=IST))
    return start, end
