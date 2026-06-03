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
from qp.utils.maps.rates.leg_type import LegType
from qp.time.date.daycount import Daycount, yearfrac
from qp.time.date.dateroll import Dateroll
from qp.curves.ir_curve import IRCurve

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
    dfs = np.array(discount_factors)
    n = len(dfs)
    tenors = np.array([i * 0.25 for i in range(1, n + 1)])
    return IRCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_360,
        currency=Currency.USD,
        curve_name="USD_TEST",
        tenors=tenors,
        discount_factors=dfs,
        extrapolate=True,
    )


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
    curve = make_flat_ois_curve(r, Daycount.THIRTY_360)

    schedules = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=curve).price(
        make_irs(
            leg_one=make_fixed_leg(start_date=VALUATION_DATE),
            leg_two=make_float_leg(
                daycount=Daycount.THIRTY_360, start_date=VALUATION_DATE
            ),
        )
    )
    # each forward rate ≈ r; check first few periods
    for cf, tau in zip(schedules[1].cashflows, schedules[1].accrual_yearfracs_periodic):
        implied_rate = abs(cf) / (NOTIONAL * tau)
        assert implied_rate == pytest.approx((np.exp(r * tau) - 1) / tau, abs=1e-4)


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

    dfs = curve.get_discount_factors(
        yearfrac(curve.at_date, schedules[1].accrual_end_dates, curve.daycount)
    )

    dfs_offset = np.ones(len(dfs))
    dfs_offset[1:] = dfs[:-1]
    dfs_offset[0] = curve.get_discount_factors(
        yearfrac(curve.at_date, schedules[0].start_date, curve.daycount)
    )
    taus = schedules[1].accrual_yearfracs_periodic
    expected_rates = (dfs_offset / dfs - 1) / taus

    for cf, tau, expected_rate in zip(schedules[1].cashflows, taus, expected_rates):
        implied_rate = abs(cf) / (NOTIONAL * tau)
        assert implied_rate == pytest.approx(expected_rate, rel=1e-6)


# --- OIS helpers ---

OIS_START_DATE = dt.date(2026, 5, 28)  # before VALUATION_DATE — enables mid-live tests
OIS_END_DATE = dt.date(2026, 9, 1)


def make_ois_leg(**kwargs):
    defaults = dict(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=OIS_END_DATE,
        payment_frequency=Frequency.QUARTERLY,
        collateral_currency=Currency.USD,
        daycount=Daycount.ACT_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.RECEIVE,
        index=FloatingIndex.SOFR,
        leg_type=LegType.OIS,
        lookback=0,
    )
    return IRFloatingLeg(**{**defaults, **kwargs})


def make_flat_ois_curve(r: float, daycount: Daycount = Daycount.ACT_360):
    """Returns exp(-r * tau) for any scalar or array yearfrac input."""
    curve = MagicMock()
    curve.get_discount_factors.side_effect = lambda tau: np.exp(-r * np.asarray(tau))
    curve.at_date = VALUATION_DATE
    curve.daycount = daycount
    return curve


# --- OIS validation ---


def test_raises_if_ois_mid_live_fixings_wrong_length():
    """Providing the wrong number of historic fixings for a mid-live OIS should raise."""
    ois_leg = make_ois_leg(start_date=OIS_START_DATE, end_date=OIS_END_DATE)
    irs = make_irs(leg_two=ois_leg)
    with pytest.raises(ValueError):
        IRSModel(
            valuation_date=VALUATION_DATE,
            leg_two_curve=make_flat_ois_curve(0.05),
            leg_two_historic_fixings=np.array([0.05]),  # wrong length
        ).price(irs)


# --- OIS fully forward ---


def test_ois_fully_forward_cashflow_count():
    """Quarterly OIS over ~3 months starting at valuation date should produce 1 cashflow."""
    ois_leg = make_ois_leg(start_date=START_DATE, end_date=OIS_END_DATE)
    schedules = IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=make_flat_ois_curve(0.05),
    ).price(make_irs(leg_two=ois_leg))
    assert len(schedules[1].cashflows) == 1


def test_ois_fully_forward_telescoping():
    """For a fully forward single-period OIS, cashflow = notional × (P_start/P_end − 1).

    With a flat curve exp(-r*t), P_start/P_end = exp(-r*tau_start) / exp(-r*tau_end).
    Compute the expected cashflow by hand and fill in below.
    """
    r = 0.05
    ois_leg = make_ois_leg(start_date=START_DATE, end_date=OIS_END_DATE)
    schedules = IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=make_flat_ois_curve(r),
    ).price(make_irs(leg_two=ois_leg))
    expected_cashflow = NOTIONAL * (
        np.exp(
            -r * yearfrac(VALUATION_DATE, START_DATE, Daycount.ACT_360, Currency.USD)
        )
        / np.exp(
            -r * yearfrac(VALUATION_DATE, OIS_END_DATE, Daycount.ACT_360, Currency.USD)
        )
        - 1
    )  # notional × (exp(-r * tau_start) / exp(-r * tau_end) - 1)
    assert schedules[1].cashflows[0] == pytest.approx(expected_cashflow, rel=1e-6)


# --- OIS mid-live ---


def test_ois_mid_live_first_period_cashflow():
    """Mid-live OIS: first period compounds historic fixings with forward rates.

    Set start_date before VALUATION_DATE. Provide the correct number of historic
    fixings (one per overnight period from start_date to valuation_date). Compute
    the expected first-period cashflow by hand and fill in below.
    """
    historic_fixings = np.array(
        [0.04, 0.05]
    )  # one rate per overnight period from OIS_START_DATE to VALUATION_DATE
    ois_leg = make_ois_leg(start_date=OIS_START_DATE, end_date=OIS_END_DATE)
    schedules = IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=make_flat_ois_curve(0.05),
        leg_two_historic_fixings=historic_fixings,
    ).price(make_irs(leg_two=ois_leg))

    ois_fixing = ((1 + 0.04 * 1 / 360) * (1 + 0.05 * 3 / 360) - 1) / (4 / 360)
    expected_first_cashflow = NOTIONAL * ois_fixing * 4 / 360
    assert schedules[1].cashflows[0] == pytest.approx(expected_first_cashflow, rel=1e-6)


# --- OIS lookback tests ---


def test_ois_lookback_edge_case_validation_raises():
    """Providing the wrong number of historic fixings for a lookback OIS should raise."""
    ois_leg = make_ois_leg(start_date=OIS_START_DATE, end_date=OIS_END_DATE, lookback=2)
    irs = make_irs(leg_two=ois_leg)
    with pytest.raises(ValueError):
        IRSModel(
            valuation_date=VALUATION_DATE,
            leg_two_curve=make_flat_ois_curve(0.05),
            leg_two_historic_fixings=([0.05]),  # wrong length, expected is 2
        ).price(irs)
    pass


def test_ois_lookback_edge_case_validation_does_not_raise():
    """Providing the correct number of historic fixings for a lookback OIS should not raise."""
    ois_leg = make_ois_leg(start_date=OIS_START_DATE, end_date=OIS_END_DATE, lookback=2)
    irs = make_irs(leg_two=ois_leg)
    IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=make_flat_ois_curve(0.05),
        leg_two_historic_fixings=([0.05, 0.06]),  # expected is 2
    ).price(irs)
    pass


def test_ois_mid_live_simple():
    """Test mid-live OIS calculates the correct OIS rate for the first period"""
    ois_leg = make_ois_leg(
        start_date=OIS_START_DATE, end_date=dt.date(2026, 9, 4), lookback=2
    )
    irs = make_irs(leg_two=ois_leg)
    historic_fixings = [
        0.05,
        0.06,
        0.07,
        0.08,
    ]  # dates = may28, may29, jun1, jun2, jun3 >> deltas = 1, 3, 1, 1
    ois_curve = IRCurve(
        VALUATION_DATE,
        Daycount.ACT_360,
        Currency.USD,
        "SOFR",
        [0, 0.1, 0.2, 0.3],
        discount_factors=[1, 0.9998, 0.9987, 0.9964],
    )

    df_june_2 = np.exp(0 + np.log(0.9998) * ((1 / 360 - 0) / (0.1 - 0)))
    expected_fwd_rate_jun3_jun4 = (1 / df_june_2 - 1) / (1 / 360)

    expected_ois_rate_first_period = (
        np.prod(
            np.array(
                [
                    (1 + 0.05 * 1 / 360),
                    (1 + 0.06 * 3 / 360),
                    (1 + 0.07 * 1 / 360),
                    (1 + 0.08 * 1 / 360),
                    (1 + expected_fwd_rate_jun3_jun4 * 1 / 360),
                ]
            )
        )
        - 1
    ) / ((1 + 3 + 1 + 1 + 1) / 360)

    expected_cashflow_first_period = (
        NOTIONAL
        * expected_ois_rate_first_period
        * yearfrac(dt.date(2026, 5, 28), dt.date(2026, 6, 4), Daycount.ACT_360)
    )

    irs_price = IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=ois_curve,
        leg_two_historic_fixings=historic_fixings,
    ).price(irs)

    ois_first_cashflow = irs_price[1].cashflows[0]

    assert expected_cashflow_first_period == pytest.approx(ois_first_cashflow)


def test_ois_lookback_kinked():
    """With lookback=2, forward rates for future accrual days use DFs at the
    shifted dates (accrual - 2bd). On a curve with a kink at t=2/360, the
    shifted lookup Jun1→Jun2 falls in a different segment than the unshifted
    Jun3→Jun4 — so an incorrect (unshifted) implementation would produce a
    different cashflow.
    """
    ois_leg = make_ois_leg(
        start_date=OIS_START_DATE, end_date=dt.date(2026, 9, 4), lookback=2
    )
    irs = make_irs(leg_two=ois_leg)

    # Kink at t=2/360: slope in [0, 2/360] differs from [2/360, 4/360]
    ois_curve = IRCurve(
        VALUATION_DATE,
        Daycount.ACT_360,
        Currency.USD,
        "SOFR",
        [0, 2 / 360, 4 / 360, 0.2, 0.3],
        discount_factors=[
            1,
            0.8888,
            0.7777,
            0.6666,
            0.5555,
        ],  # choose values with a clear kink
    )

    historic_fixings = [
        0.05,
        0.06,
        0.07,
        0.08,
    ]  # 4 values — one per overnight period May28→May29, May29→Jun1, Jun1→Jun2, Jun2→Jun3

    # Expected forward rate: (DF(0) / DF(1/360) - 1) / (1/360)
    # DF(1/360) comes from log-linear interpolation in the [0, 2/360] segment
    df_jun2 = np.exp(0 + (1 / 360 - 0) * (np.log(0.8888) - np.log(1)) / (2 / 360 - 0))
    expected_fwd_rate_jun3_jun4 = (1 / df_jun2 - 1) / (1 / 360)
    expected_ois_rate_first_period = (
        np.prod(
            np.array(
                [
                    (1 + 0.05 * 1 / 360),
                    (1 + 0.06 * 3 / 360),
                    (1 + 0.07 * 1 / 360),
                    (1 + 0.08 * 1 / 360),
                    (1 + expected_fwd_rate_jun3_jun4 * 1 / 360),
                ]
            )
        )
        - 1
    ) / ((1 + 3 + 1 + 1 + 1) / 360)

    expected_cashflow = (
        NOTIONAL
        * expected_ois_rate_first_period
        * yearfrac(dt.date(2026, 5, 28), dt.date(2026, 6, 4), Daycount.ACT_360)
    )

    result = IRSModel(
        valuation_date=VALUATION_DATE,
        leg_two_curve=ois_curve,
        leg_two_historic_fixings=historic_fixings,
    ).price(irs)

    assert result[1].cashflows[0] == pytest.approx(expected_cashflow)


# --- price() structure ---


def test_price_returns_two_schedules():
    schedules = make_model().price(make_irs())
    assert len(schedules) == 2


def test_price_leg_order_matches_irs_legs():
    schedules = make_model().price(make_irs())
    assert schedules[0].cashflows[0] < 0  # fixed PAY leg
    assert schedules[1].cashflows[0] > 0  # float RECEIVE leg


def test_float_leg_spread_increases_receiver_pv():
    # A non-zero spread on a receiver leg adds to every cashflow — PV must be higher
    # than the same leg with spread=0.
    curve = make_ir_curve([0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92])
    leg_no_spread = make_float_leg(spread=0.0)
    leg_with_spread = make_float_leg(spread=0.01)
    irs_no_spread = IRS(leg_one=None, leg_two=leg_no_spread)
    irs_with_spread = IRS(leg_one=None, leg_two=leg_with_spread)
    model = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=curve)
    pv_no_spread = sum(model.price(irs_no_spread)[0].cashflows)
    pv_with_spread = sum(model.price(irs_with_spread)[0].cashflows)
    assert pv_with_spread > pv_no_spread
