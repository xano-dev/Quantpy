import datetime as dt
from unittest.mock import MagicMock
import numpy as np
import pytest

from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.models.rates.irs_model import IRSModel
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll

VALUATION_DATE = dt.date(2026, 6, 1)
START_DATE = dt.date(2026, 6, 3)  # spot-starting T+2
END_DATE_2Y = dt.date(2028, 6, 3)
END_DATE_5Y = dt.date(2031, 6, 3)
NOTIONAL = 10_000_000
FIXED_RATE = 0.05


def make_fixed_leg(**kwargs):
    defaults = dict(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE_2Y,
        payment_frequency=Frequency.SEMI_ANNUAL,
        collateral_currency=Currency.USD,
        daycount=Daycount.THIRTY_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.PAY,
        fixed_rate=FIXED_RATE,
    )
    return IRFixedLeg(**{**defaults, **kwargs})


def make_float_leg(**kwargs):
    defaults = dict(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE_2Y,
        payment_frequency=Frequency.QUARTERLY,
        collateral_currency=Currency.USD,
        daycount=Daycount.ACT_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.RECEIVE,
        index=FloatingIndex.SOFR,
    )
    return IRFloatingLeg(**{**defaults, **kwargs})


def make_ir_curve(discount_factors):
    """Mock IRCurve whose get_discount_factors returns the given array."""
    curve = MagicMock()
    curve.get_discount_factors.return_value = np.array(discount_factors)
    return curve


def make_irs(**kwargs):
    defaults = dict(
        leg_one=make_fixed_leg(),
        leg_two=make_float_leg(),
    )
    return IRS(**{**defaults, **kwargs})


def make_model(curve=None, **kwargs):
    if curve is None:
        curve = make_ir_curve([0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92])
    defaults = dict(
        valuation_date=VALUATION_DATE,
        leg_two_curve=curve,
    )
    return IRSModel(**{**defaults, **kwargs})


# --- Validation ---


def test_raises_if_float_leg_has_no_curve():
    with pytest.raises(ValueError):
        IRSModel(valuation_date=VALUATION_DATE).price(make_irs())


def test_raises_if_seasoned_swap_has_no_historic_fixing():
    seasoned_start = dt.date(2025, 1, 1)
    irs = make_irs(
        leg_two=make_float_leg(start_date=seasoned_start, end_date=dt.date(2027, 1, 1))
    )
    with pytest.raises(ValueError):
        make_model().price(irs)


def test_raises_if_float_leg_historic_fixing_is_not_scalar():
    seasoned_start = dt.date(2025, 1, 1)
    irs = make_irs(
        leg_two=make_float_leg(start_date=seasoned_start, end_date=dt.date(2027, 1, 1))
    )
    with pytest.raises(ValueError):
        IRSModel(
            valuation_date=VALUATION_DATE,
            leg_two_curve=make_ir_curve([0.99, 0.98, 0.97, 0.96]),
            leg_two_historic_fixings=[0.05, 0.05],  # should be scalar
        ).price(irs)


# --- Fixed leg ---


def test_fixed_leg_cashflow_count():
    """2Y semi-annual fixed leg should produce 4 cashflows."""
    schedules = make_model().price(make_irs())
    fixed_schedule = schedules[0]
    assert len(fixed_schedule.cashflows) == 4


def test_fixed_leg_cashflows_are_negative_when_paying():
    schedules = make_model().price(
        make_irs(leg_one=make_fixed_leg(pay_receive=PayReceive.PAY))
    )
    assert all(cf < 0 for cf in schedules[0].cashflows)


def test_fixed_leg_cashflows_are_positive_when_receiving():
    schedules = make_model().price(
        make_irs(leg_one=make_fixed_leg(pay_receive=PayReceive.RECEIVE))
    )
    assert all(cf > 0 for cf in schedules[0].cashflows)


def test_fixed_leg_cashflow_magnitude():
    """Semi-annual 30/360: each coupon ≈ notional × rate × 0.5"""
    schedules = make_model().price(
        make_irs(leg_one=make_fixed_leg(pay_receive=PayReceive.RECEIVE))
    )
    assert schedules[0].cashflows[0] == pytest.approx(
        NOTIONAL * FIXED_RATE * 0.5, rel=1e-4
    )


def test_fixed_leg_cashflows_sum():
    """Total undiscounted fixed cashflows over 2Y."""
    schedules = make_model().price(
        make_irs(leg_one=make_fixed_leg(pay_receive=PayReceive.RECEIVE))
    )
    assert schedules[0].cashflows.sum() == pytest.approx(
        NOTIONAL * FIXED_RATE * 0.5 * 4, rel=1e-4
    )


# --- Float leg ---


def test_float_leg_cashflow_count():
    """2Y quarterly float leg should produce 8 cashflows."""
    schedules = make_model().price(make_irs())
    assert len(schedules[1].cashflows) == 8


def test_float_leg_cashflows_are_positive_when_receiving():
    schedules = make_model().price(
        make_irs(leg_two=make_float_leg(pay_receive=PayReceive.RECEIVE))
    )
    assert all(cf > 0 for cf in schedules[1].cashflows)


def test_float_leg_cashflows_are_negative_when_paying():
    schedules = make_model().price(
        make_irs(leg_two=make_float_leg(pay_receive=PayReceive.PAY))
    )
    assert all(cf < 0 for cf in schedules[1].cashflows)


def test_float_leg_forward_rate_from_flat_curve():
    """With a flat discount curve exp(-r*T), each forward rate should equal r."""
    r = 0.05
    n_periods = 8
    taus = np.array([i * 0.25 for i in range(1, n_periods + 1)])
    dfs = 1 / (1 + r * 0.25) ** (np.arange(taus.size) + 1)
    curve = make_ir_curve(dfs)

    schedules = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=curve).price(
        make_irs(leg_two=make_float_leg(daycount=Daycount.THIRTY_360))
    )
    # each forward rate ≈ r; check first few periods
    for cf, tau in zip(schedules[1].cashflows, schedules[1].accrual_yearfracs_periodic):
        implied_rate = abs(cf) / (NOTIONAL * tau)
        assert implied_rate == pytest.approx(r, abs=1e-4)


def test_float_leg_forward_rates_non_flat_curve():
    """Forward rates derived from DF ratio match the simply-compounded formula directly.

    Given dfs = [df_1, ..., df_8] and dfs_offset = [1, df_1, ..., df_7],
    expected_rate_i = (dfs_offset_i / dfs_i - 1) / tau_i
    """
    dfs = np.array([0.990, 0.979, 0.967, 0.954, 0.940, 0.925, 0.909, 0.892])
    curve = make_ir_curve(dfs)

    schedules = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=curve).price(
        make_irs()
    )

    dfs_offset = np.ones(len(dfs))
    dfs_offset[1:] = dfs[:-1]
    taus = schedules[1].accrual_yearfracs_periodic
    expected_rates = (dfs_offset / dfs - 1) / taus

    for cf, tau, expected_rate in zip(schedules[1].cashflows, taus, expected_rates):
        implied_rate = abs(cf) / (NOTIONAL * tau)
        assert implied_rate == pytest.approx(expected_rate, rel=1e-6)


# --- price() structure ---


def test_price_returns_two_schedules():
    schedules = make_model().price(make_irs())
    assert len(schedules) == 2


def test_price_leg_order_matches_irs_legs():
    schedules = make_model().price(make_irs())
    assert schedules[0].cashflows[0] < 0  # fixed PAY leg
    assert schedules[1].cashflows[0] > 0  # float RECEIVE leg
