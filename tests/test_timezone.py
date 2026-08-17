"""Regression tests for EAT-aware "today" helpers.

The bot must compute "today" in the Ethiopian timezone (UTC+3), not server
local time. On UTC hosts (e.g. Render) a naive ``datetime.now()`` shows
yesterday's date between 00:00 and 03:00 EAT — the bug these tests pin down.
"""

from datetime import datetime, timezone, timedelta

import pytest

from app.db.base import EAT, get_eth_datetime, get_eth_today


def test_eth_datetime_uses_utc_plus_3():
    now = get_eth_datetime()
    assert now.utcoffset() == timedelta(hours=3)


def test_eth_today_matches_eth_datetime():
    assert get_eth_today() == get_eth_datetime().date()


def test_date_rolls_over_correctly_during_eat_midnight(monkeypatch):
    """Between 00:00–03:00 EAT, UTC is still the previous day.

    A naive server clock (UTC) would report the wrong date here; the EAT-aware
    helper must report the new Ethiopian day.
    """
    class FakeDatetime:
        @classmethod
        def now(cls, tz=None):
            # 2026-01-01 22:30 UTC == 2026-01-02 01:30 EAT
            utc_now = datetime(2026, 1, 1, 22, 30, tzinfo=timezone.utc)
            if tz is not None:
                return utc_now.astimezone(tz)
            return utc_now.replace(tzinfo=None)

    monkeypatch.setattr("app.db.base.datetime", FakeDatetime)

    # The old bug: naive datetime.now() on a UTC host reports Jan 1 here.
    naive_now = datetime(2026, 1, 1, 22, 30).replace(tzinfo=None)
    assert naive_now.date() == datetime(2026, 1, 1).date()

    # The fixed helper reports the correct Ethiopian day (already Jan 2 in EAT).
    assert get_eth_today() == datetime(2026, 1, 2).date()
    assert get_eth_datetime().date() == datetime(2026, 1, 2).date()


def test_eat_offset_is_exactly_utc_plus_3():
    assert EAT.utcoffset(None) == timedelta(hours=3)
