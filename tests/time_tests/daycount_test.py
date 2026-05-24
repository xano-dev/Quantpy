import datetime as dt
import numpy as np
import pytest
from qp.time.date.daycount import yearfrac, Daycount
from qp.utils.maps.currency.currencies import Currency

# ---- ACT/360 ----


def test_act_360_simple():
    assert yearfrac(
        dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_360
    ) == pytest.approx(182 / 360)


def test_act_360_full_year():
    assert yearfrac(
        dt.date(2024, 1, 1), dt.date(2025, 1, 1), Daycount.ACT_360
    ) == pytest.approx(366 / 360)


def test_act_360_vec():
    ends = [dt.date(2024, 7, 1), dt.date(2025, 1, 1)]
    result = yearfrac(dt.date(2024, 1, 1), ends, Daycount.ACT_360)
    expected = np.array([182 / 360, 366 / 360])
    np.testing.assert_allclose(result, expected)


def test_act_360_array_starts():
    # Paired: each start matched to its corresponding end.
    # 2024-01-01 to 2024-07-01 = 182 days
    # 2024-07-01 to 2025-01-01 = 184 days
    starts = [dt.date(2024, 1, 1), dt.date(2024, 7, 1)]
    ends = [dt.date(2024, 7, 1), dt.date(2025, 1, 1)]
    result = yearfrac(starts, ends, Daycount.ACT_360)
    expected = np.array([182 / 360, 184 / 360])
    np.testing.assert_allclose(result, expected)


def test_act_360_array_starts_single_element():
    starts = [dt.date(2024, 1, 1)]
    ends = [dt.date(2024, 7, 1)]
    result = yearfrac(starts, ends, Daycount.ACT_360)
    np.testing.assert_allclose(result, np.array([182 / 360]))


# ---- ACT/365 ----


def test_act_365_simple():
    assert yearfrac(
        dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_365
    ) == pytest.approx(182 / 365)


def test_act_365_full_year():
    assert yearfrac(
        dt.date(2024, 1, 1), dt.date(2025, 1, 1), Daycount.ACT_365
    ) == pytest.approx(366 / 365)


def test_act_365_vec():
    ends = [dt.date(2024, 7, 1), dt.date(2025, 1, 1)]
    result = yearfrac(dt.date(2024, 1, 1), ends, Daycount.ACT_365)
    expected = np.array([182 / 365, 366 / 365])
    np.testing.assert_allclose(result, expected)


def test_act_365_array_starts():
    # 2024-01-01 to 2024-07-01 = 182 days
    # 2024-07-01 to 2025-01-01 = 184 days
    starts = [dt.date(2024, 1, 1), dt.date(2024, 7, 1)]
    ends = [dt.date(2024, 7, 1), dt.date(2025, 1, 1)]
    result = yearfrac(starts, ends, Daycount.ACT_365)
    expected = np.array([182 / 365, 184 / 365])
    np.testing.assert_allclose(result, expected)


def test_act_365_array_starts_cross_year_boundary():
    # Verify holiday-year range is computed from min(starts), not just starts[0].
    # 2023-06-01 to 2023-12-01 = 183 days
    # 2024-06-01 to 2024-12-01 = 183 days
    starts = [dt.date(2023, 6, 1), dt.date(2024, 6, 1)]
    ends = [dt.date(2023, 12, 1), dt.date(2024, 12, 1)]
    result = yearfrac(starts, ends, Daycount.ACT_365)
    expected = np.array([183 / 365, 183 / 365])
    np.testing.assert_allclose(result, expected)


# ---- THIRTY/360 ----


def test_thirty_360_simple():
    assert yearfrac(
        dt.date(2024, 1, 15), dt.date(2024, 7, 15), Daycount.THIRTY_360
    ) == pytest.approx(180 / 360)


def test_thirty_360_eom_start():
    assert yearfrac(
        dt.date(2024, 1, 31), dt.date(2024, 2, 28), Daycount.THIRTY_360
    ) == pytest.approx(28 / 360)


def test_thirty_360_eom_both():
    assert yearfrac(
        dt.date(2024, 1, 31), dt.date(2024, 3, 31), Daycount.THIRTY_360
    ) == pytest.approx(60 / 360)


def test_thirty_360_multi_year():
    assert yearfrac(
        dt.date(2023, 1, 15), dt.date(2025, 1, 15), Daycount.THIRTY_360
    ) == pytest.approx(2.0)


def test_thirty_360_vec():
    ends = [dt.date(2024, 7, 15), dt.date(2024, 3, 31)]
    result = yearfrac(dt.date(2024, 1, 15), ends, Daycount.THIRTY_360)
    expected = np.array([180 / 360, 76 / 360])
    np.testing.assert_allclose(result, expected)


def test_thirty_360_vec_eom():
    ends = [dt.date(2024, 2, 28), dt.date(2024, 3, 31)]
    result = yearfrac(dt.date(2024, 1, 31), ends, Daycount.THIRTY_360)
    expected = np.array([28 / 360, 60 / 360])
    np.testing.assert_allclose(result, expected)


def test_thirty_360_array_starts():
    # Period 0: 2024-01-15 to 2024-07-15 = 180/360
    # Period 1: 2024-07-15 to 2025-01-15 = 180/360
    starts = [dt.date(2024, 1, 15), dt.date(2024, 7, 15)]
    ends = [dt.date(2024, 7, 15), dt.date(2025, 1, 15)]
    result = yearfrac(starts, ends, Daycount.THIRTY_360)
    expected = np.array([180 / 360, 180 / 360])
    np.testing.assert_allclose(result, expected)


def test_thirty_360_array_starts_eom():
    # Both periods have a day-31 start, exercising the vectorised EOM branch.
    # Period 0: 2024-01-31 to 2024-03-31 = 60/360 (both adjusted to 30)
    # Period 1: 2024-03-31 to 2024-05-31 = 60/360 (both adjusted to 30)
    starts = [dt.date(2024, 1, 31), dt.date(2024, 3, 31)]
    ends = [dt.date(2024, 3, 31), dt.date(2024, 5, 31)]
    result = yearfrac(starts, ends, Daycount.THIRTY_360)
    expected = np.array([60 / 360, 60 / 360])
    np.testing.assert_allclose(result, expected)


def test_thirty_360_array_starts_mixed_eom():
    # Period 0: day-31 start, day-31 end  -> both clamped to 30, result = 60/360
    # Period 1: day-15 start, day-15 end  -> no clamping, result = 180/360
    starts = [dt.date(2024, 1, 31), dt.date(2024, 1, 15)]
    ends = [dt.date(2024, 3, 31), dt.date(2024, 7, 15)]
    result = yearfrac(starts, ends, Daycount.THIRTY_360)
    expected = np.array([60 / 360, 180 / 360])
    np.testing.assert_allclose(result, expected)


# ---- THIRTY/365 ----


def test_thirty_365_simple():
    assert yearfrac(
        dt.date(2024, 1, 15), dt.date(2024, 7, 15), Daycount.THIRTY_365
    ) == pytest.approx(180 / 365)


def test_thirty_365_vec():
    ends = [dt.date(2024, 7, 15), dt.date(2025, 1, 15)]
    result = yearfrac(dt.date(2024, 1, 15), ends, Daycount.THIRTY_365)
    expected = np.array([180 / 365, 365 / 365])
    np.testing.assert_allclose(result, expected)


def test_thirty_365_array_starts():
    # Period 0: 2024-01-15 to 2024-07-15 = 180/365
    # Period 1: 2024-07-15 to 2025-01-15 = 180/365
    starts = [dt.date(2024, 1, 15), dt.date(2024, 7, 15)]
    ends = [dt.date(2024, 7, 15), dt.date(2025, 1, 15)]
    result = yearfrac(starts, ends, Daycount.THIRTY_365)
    expected = np.array([180 / 365, 185 / 365])
    np.testing.assert_allclose(result, expected)


# ---- BUS/252 ----


def test_bus_252_no_holidays():
    assert yearfrac(
        dt.date(2025, 1, 6), dt.date(2025, 1, 13), Daycount.BUS_252
    ) == pytest.approx(5 / 252)


def test_bus_252_with_holiday():
    # Dec 30 (Mon), Dec 31 (Tue), [Jan 1 = New Year, excluded], Jan 2 (Thu), Jan 3 (Fri) = 4 bus days
    assert yearfrac(
        dt.date(2024, 12, 30),
        dt.date(2025, 1, 6),
        Daycount.BUS_252,
        currency_1=Currency.USD,
    ) == pytest.approx(4 / 252)


def test_bus_252_vec_no_holidays():
    ends = [dt.date(2025, 1, 13), dt.date(2025, 1, 20)]
    result = yearfrac(dt.date(2025, 1, 6), ends, Daycount.BUS_252)
    expected = np.array([5 / 252, 10 / 252])
    np.testing.assert_allclose(result, expected)


def test_bus_252_vec_with_holiday():
    ends = [dt.date(2025, 1, 6), dt.date(2025, 1, 13)]
    result = yearfrac(
        dt.date(2024, 12, 30), ends, Daycount.BUS_252, currency_1=Currency.USD
    )
    # Dec 30 to Jan 6: 4 bus days (New Year excluded); Jan 6 to Jan 13 adds 5 more = 9
    expected = np.array([4 / 252, 9 / 252])
    np.testing.assert_allclose(result, expected)


def test_bus_252_array_starts_no_holidays():
    # Period 0: 2025-01-06 (Mon) to 2025-01-13 (Mon) = 5 bus days
    # Period 1: 2025-01-13 (Mon) to 2025-01-20 (Mon) = 5 bus days
    starts = [dt.date(2025, 1, 6), dt.date(2025, 1, 13)]
    ends = [dt.date(2025, 1, 13), dt.date(2025, 1, 20)]
    result = yearfrac(starts, ends, Daycount.BUS_252)
    expected = np.array([5 / 252, 5 / 252])
    np.testing.assert_allclose(result, expected)


def test_bus_252_array_starts_with_holiday():
    # Period 0: Dec 30 to Jan 6 = 4 bus days (New Year excluded)
    # Period 1: Jan 6 to Jan 13 = 5 bus days
    starts = [dt.date(2024, 12, 30), dt.date(2025, 1, 6)]
    ends = [dt.date(2025, 1, 6), dt.date(2025, 1, 13)]
    result = yearfrac(starts, ends, Daycount.BUS_252, currency_1=Currency.USD)
    expected = np.array([4 / 252, 5 / 252])
    np.testing.assert_allclose(result, expected)


def test_bus_252_array_starts_holiday_range_covers_all_start_years():
    # Starts span two calendar years; holiday fetching must use min(starts).year,
    # not just the first element's year, to correctly exclude holidays in both years.
    # Period 0: 2023-12-27 (Wed) to 2024-01-03 (Wed) = 4 bus days (Jan 1 excluded)
    # Period 1: 2024-12-27 (Fri) to 2025-01-03 (Fri) = 4 bus days (Jan 1 excluded)
    starts = [dt.date(2023, 12, 27), dt.date(2024, 12, 27)]
    ends = [dt.date(2024, 1, 3), dt.date(2025, 1, 3)]
    result = yearfrac(starts, ends, Daycount.BUS_252, currency_1=Currency.USD)
    expected = np.array([4 / 252, 4 / 252])
    np.testing.assert_allclose(result, expected)


# ---- RETURN TYPE ----


def test_scalar_returns_float():
    result = yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_360)
    assert isinstance(result, float)


def test_vec_returns_ndarray():
    result = yearfrac(dt.date(2024, 1, 1), [dt.date(2024, 7, 1)], Daycount.ACT_360)
    assert isinstance(result, np.ndarray)


def test_array_starts_returns_ndarray():
    starts = [dt.date(2024, 1, 1), dt.date(2024, 7, 1)]
    ends = [dt.date(2024, 7, 1), dt.date(2025, 1, 1)]
    result = yearfrac(starts, ends, Daycount.ACT_360)
    assert isinstance(result, np.ndarray)


# ---- INVALID ----


def test_invalid_daycount():
    with pytest.raises(KeyError):
        yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), "ACT/999")


def run_tests():
    pytest.main([__file__, "-v"])
