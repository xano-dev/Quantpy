import datetime as dt
import pytest
from qp.utils.daycount import yearfrac, Daycount

# ---- ACT/360 ----

def test_act_360_simple():
    # 182 actual days (Jan has 31, Feb has 29 in leap year 2024, etc.) / 360
    assert yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_360) == pytest.approx(182 / 360)

def test_act_360_full_year():
    # 2024 is a leap year so 366 actual days / 360
    assert yearfrac(dt.date(2024, 1, 1), dt.date(2025, 1, 1), Daycount.ACT_360) == pytest.approx(366 / 360)

# ---- ACT/365 ----

def test_act_365_simple():
    # Same 182 actual days, but denominator is fixed at 365
    assert yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_365) == pytest.approx(182 / 365)

def test_act_365_full_year():
    # Leap year gives 366 days but denominator stays 365 — ratio > 1
    assert yearfrac(dt.date(2024, 1, 1), dt.date(2025, 1, 1), Daycount.ACT_365) == pytest.approx(366 / 365)

# ---- THIRTY/360 ----

def test_thirty_360_simple():
    # 6 months × 30 = 180 days; no EOM adjustments needed (neither date is 31st)
    assert yearfrac(dt.date(2024, 1, 15), dt.date(2024, 7, 15), Daycount.THIRTY_360) == pytest.approx(180 / 360)

def test_thirty_360_eom_start():
    # D1=31 → adjusted to 30. D2=28 (Feb 28 is not 31, so unchanged).
    # Day count = (0*360) + (1*30) + (28 - 30) = 28 days
    assert yearfrac(dt.date(2024, 1, 31), dt.date(2024, 2, 28), Daycount.THIRTY_360) == pytest.approx(28 / 360)

def test_thirty_360_eom_both():
    # D1=31 → 30, D2=31 → 30 (because D1 became 30).
    # Day count = (0*360) + (2*30) + (30 - 30) = 60 days
    assert yearfrac(dt.date(2024, 1, 31), dt.date(2024, 3, 31), Daycount.THIRTY_360) == pytest.approx(60 / 360)

def test_thirty_360_multi_year():
    # Exact two-year span with no EOM complications — should be exactly 2.0
    assert yearfrac(dt.date(2023, 1, 15), dt.date(2025, 1, 15), Daycount.THIRTY_360) == pytest.approx(2.0)

# ---- THIRTY/365 ----

def test_thirty_365_simple():
    # Same 30/360 day count (180), but divided by 365 instead
    assert yearfrac(dt.date(2024, 1, 15), dt.date(2024, 7, 15), Daycount.THIRTY_365) == pytest.approx(180 / 365)

# ---- BUS/252 ----

def test_bus_252_no_holidays():
    # Mon Jan 6 to Mon Jan 13 2025: one standard working week = 5 business days
    assert yearfrac(dt.date(2025, 1, 6), dt.date(2025, 1, 13), Daycount.BUS_252) == pytest.approx(5 / 252)

def test_bus_252_with_holiday():
    # Dec 30 (Mon), Dec 31 (Tue), [Jan 1 = New Year, excluded], Jan 2 (Thu), Jan 3 (Fri) = 4 bus days
    assert yearfrac(dt.date(2024, 12, 30), dt.date(2025, 1, 6), Daycount.BUS_252, currency="USD") == pytest.approx(4 / 252)

# ---- INVALID ----

def test_invalid_daycount():
    with pytest.raises(KeyError):
        yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), "ACT/999")

def run_tests():
    pytest.main([__file__, "-v"])