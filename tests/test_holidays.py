import pytest
from app.holidays import get_month_holidays, get_day_type

def test_tir_1_is_not_christmas():
    """Verify Tir 1 is not listed as Christmas."""
    holidays = get_month_holidays(5, 2018)  # Tir 2018
    assert 1 not in holidays

def test_hidar_20_is_not_national_unity_day():
    """Verify Hidar 20 is not listed in holidays."""
    holidays = get_month_holidays(3, 2018)  # Hidar 2018
    assert 20 not in holidays

def test_christmas_regular_year():
    """Verify Ethiopian Christmas on a regular year (Tahsas 29)."""
    holidays = get_month_holidays(4, 2018)  # Tahsas 2018 (non-leap year)
    assert 29 in holidays
    assert holidays[29]["key"] == "gena"
    assert 28 in holidays
    assert holidays[28]["key"] == "gena_eve"

def test_christmas_leap_year():
    """Verify Ethiopian Christmas on a leap year (Zemene Lukas - 2015 EC)."""
    holidays = get_month_holidays(4, 2015)  # Tahsas 2015 (leap year)
    assert 28 in holidays
    assert holidays[28]["key"] == "gena"
    assert 27 in holidays
    assert holidays[27]["key"] == "gena_eve"
