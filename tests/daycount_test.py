import datetime as dt
import numpy as np
import pytest
from qp.time.daycount import yearfrac, Daycount
from qp.utils.maps.currencies import Currency

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
    # Both EOM cases in one vectorised call — D1=31 adjusted to 30 for all
    ends = [dt.date(2024, 2, 28), dt.date(2024, 3, 31)]
    result = yearfrac(dt.date(2024, 1, 31), ends, Daycount.THIRTY_360)
    expected = np.array([28 / 360, 60 / 360])
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
    # Dec 30–Jan 6: 4 bus days (New Year excluded); Jan 6–13 adds 5 more = 9
    expected = np.array([4 / 252, 9 / 252])
    np.testing.assert_allclose(result, expected)


# ---- RETURN TYPE ----


def test_scalar_returns_float():
    result = yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), Daycount.ACT_360)
    assert isinstance(result, float)


def test_vec_returns_ndarray():
    result = yearfrac(dt.date(2024, 1, 1), [dt.date(2024, 7, 1)], Daycount.ACT_360)
    assert isinstance(result, np.ndarray)


# ---- INVALID ----


def test_invalid_daycount():
    with pytest.raises(KeyError):
        yearfrac(dt.date(2024, 1, 1), dt.date(2024, 7, 1), "ACT/999")


def run_tests():
    pytest.main([__file__, "-v"])
