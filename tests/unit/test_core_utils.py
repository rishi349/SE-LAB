from datetime import UTC, date, datetime

import pytest

from app.core import ids
from app.core.clock import IST, from_db, ist_dates_to_utc_range, ist_day_window, to_db
from app.core.money import (
    MAX_DAILY_OUTGOING_PAISE,
    MAX_SINGLE_TRANSFER_PAISE,
    format_rupees,
    is_paise,
)
from app.core.rate_limit import SlidingWindowRateLimiter


class TestMoney:
    def test_limits_are_integer_paise(self):
        assert MAX_SINGLE_TRANSFER_PAISE == 5_000_000  # ₹50,000
        assert MAX_DAILY_OUTGOING_PAISE == 10_000_000  # ₹1,00,000
        assert isinstance(MAX_SINGLE_TRANSFER_PAISE, int)

    @pytest.mark.parametrize(
        ("paise", "text"),
        [(0, "0.00"), (5, "0.05"), (100, "1.00"), (123456, "1234.56"), (-250, "-2.50")],
    )
    def test_format_rupees(self, paise, text):
        assert format_rupees(paise) == text

    @pytest.mark.parametrize("bad", [1.5, "100", True, None])
    def test_non_integer_money_is_rejected(self, bad):
        assert not is_paise(bad)
        with pytest.raises(TypeError):
            format_rupees(bad)


class TestClock:
    def test_round_trip_is_utc_and_sortable(self):
        moment = datetime(2026, 1, 2, 3, 4, 5, 6, tzinfo=UTC)
        assert to_db(moment) == "2026-01-02T03:04:05.000006Z"
        assert from_db(to_db(moment)) == moment
        assert to_db(moment) < to_db(datetime(2026, 1, 2, 3, 4, 5, 7, tzinfo=UTC))

    def test_naive_datetimes_are_refused(self):
        with pytest.raises(ValueError):
            to_db(datetime(2026, 1, 1))

    def test_ist_day_starts_at_ist_midnight(self):
        # 2026-11-19 23:59 IST == 18:29 UTC
        late = datetime(2026, 11, 19, 23, 59, tzinfo=IST)
        start, end = ist_day_window(late)
        assert start == datetime(2026, 11, 18, 18, 30, tzinfo=UTC)
        assert end == datetime(2026, 11, 19, 18, 30, tzinfo=UTC)
        # one minute after IST midnight belongs to the next window
        next_start, _ = ist_day_window(datetime(2026, 11, 20, 0, 1, tzinfo=IST))
        assert next_start == end

    def test_date_filter_range_is_inclusive_ist(self):
        start, end = ist_dates_to_utc_range(date(2026, 11, 1), date(2026, 11, 1))
        assert start == "2026-10-31T18:30:00.000000Z"
        assert end == "2026-11-01T18:30:00.000000Z"
        assert ist_dates_to_utc_range(None, None) == (None, None)


class TestIds:
    def test_formats(self):
        import re

        assert re.match(ids.USER_ID_PATTERN, ids.new_user_id())
        assert re.match(ids.TRANSACTION_ID_PATTERN, ids.new_transaction_id())
        assert re.match(ids.RUN_ID_PATTERN, ids.new_run_id())
        assert ids.new_wallet_id().startswith("WAL")

    def test_ids_are_unique(self):
        assert len({ids.new_transaction_id() for _ in range(2000)}) == 2000


class TestRateLimiter:
    def test_blocks_after_limit_then_recovers(self):
        now = [0.0]
        limiter = SlidingWindowRateLimiter(clock=lambda: now[0])
        assert all(limiter.hit("k", 3, 60) is None for _ in range(3))
        retry = limiter.hit("k", 3, 60)
        assert retry is not None and retry > 0
        assert limiter.hit("other", 3, 60) is None  # keys are independent
        now[0] = 61.0
        assert limiter.hit("k", 3, 60) is None
