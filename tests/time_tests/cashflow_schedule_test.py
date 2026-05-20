import pytest
import datetime as dt
import numpy as np

from qp.time.cashflows.cashflow_schedule import (
    CashFlowSchedule,
    PeriodicCashFlowSchedule,
)
from qp.time.daycount import Daycount
from qp.time.dateroll import Dateroll, apply_payment_lag, roll_day
from qp.utils.maps.currency.currencies import Currency

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

START = dt.date(2026, 1, 1)
END = dt.date(2026, 12, 31)
FREQUENCY = "quarterly"
CURRENCY = Currency.USD
DAYCOUNT = Daycount.ACT_360
DATEROLL = Dateroll.MODIFIED_FOLLOWING
CASHFLOWS = np.ones(4)

EXPLICIT_DATES = [
    dt.date(2026, 3, 31),
    dt.date(2026, 6, 30),
    dt.date(2026, 9, 30),
    dt.date(2026, 12, 31),
]

# Raw quarter-end dates for 2026 all fall on weekdays, so rolling leaves them
# unchanged under MODIFIED_FOLLOWING.  The expected accrual / payment dates
# are therefore identical in the default (lag=0) fixture; a separate fixture
# exercises the lag and rolling behaviour explicitly.
EXPECTED_ACCRUAL_END_DATES = [
    dt.date(2026, 3, 31),  # Tuesday
    dt.date(2026, 6, 30),  # Tuesday
    dt.date(2026, 9, 30),  # Wednesday
    dt.date(2026, 12, 31),  # Thursday
]

EXPECTED_PAYMENT_DATES_NO_LAG = EXPECTED_ACCRUAL_END_DATES  # roll_day is a no-op here

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def periodic():
    """Default periodic schedule: no payment lag, MODIFIED_FOLLOWING dateroll."""
    return PeriodicCashFlowSchedule(
        start_date=START,
        end_date=END,
        frequency=FREQUENCY,
        currency=CURRENCY,
        daycount=DAYCOUNT,
        dateroll=DATEROLL,
        cashflows=CASHFLOWS,
    )


@pytest.fixture
def periodic_with_lag():
    """
    Quarterly schedule with a 2-business-day payment lag.

    Uses a start/end window where all rolled+lagged payment dates visibly
    differ from the raw accrual end dates:

        - 2027-03-31 (Wednesday) +2 BD lands on 2027-04-02 (Friday)
        - 2027-06-30 (Wednesday) +2 BD lands on 2027-07-02 (Friday)
        - 2027-09-30 (Thursday)  +2 BD lands on 2027-10-04 (Monday, skips weekend)
        - 2027-12-31 (Friday)    +2 BD lands on 2028-01-04 (Thursday, skips weekend)
    """
    return PeriodicCashFlowSchedule(
        start_date=dt.date(2027, 1, 1),
        end_date=dt.date(2027, 12, 31),
        frequency=FREQUENCY,
        currency=CURRENCY,
        daycount=DAYCOUNT,
        dateroll=DATEROLL,
        cashflows=CASHFLOWS,
        payment_lag=2,
    )


@pytest.fixture
def periodic_weekend_roll():
    """
    Schedule whose raw accrual end date falls on a weekend so that
    roll_day() produces a different payment date even at lag=0.

    Monthly from 2026-04-01 to 2026-05-31. The raw end 2026-05-31 is a Sunday,
    so MODIFIED_FOLLOWING rolls it back to 2026-05-29 (Friday, same month).
    """
    return PeriodicCashFlowSchedule(
        start_date=dt.date(2026, 4, 1),
        end_date=dt.date(2026, 5, 31),
        frequency="monthly",
        currency=CURRENCY,
        daycount=DAYCOUNT,
        dateroll=DATEROLL,
        cashflows=np.ones(2),
    )


@pytest.fixture
def base():
    return CashFlowSchedule(
        start_date=START,
        payment_dates=EXPLICIT_DATES,
        cashflows=CASHFLOWS,
        currency=CURRENCY,
        daycount=DAYCOUNT,
    )


@pytest.fixture
def base_with_accrual_dates():
    """
    Base schedule where payment_dates and accrual_end_dates are explicitly
    different. Payment dates are shifted one month forward relative to
    accrual ends so that the two yearfrac arrays are measurably distinct.
    """
    accrual_ends = [
        dt.date(2026, 3, 31),
        dt.date(2026, 6, 30),
        dt.date(2026, 9, 30),
        dt.date(2026, 12, 31),
    ]
    payment_dates = [
        dt.date(2026, 4, 30),
        dt.date(2026, 7, 31),
        dt.date(2026, 10, 30),
        dt.date(2027, 1, 31),
    ]
    return CashFlowSchedule(
        start_date=START,
        payment_dates=payment_dates,
        cashflows=CASHFLOWS,
        currency=CURRENCY,
        daycount=DAYCOUNT,
        accrual_end_dates=accrual_ends,
    )


# ===========================================================================
# CashFlowSchedule (base)
# ===========================================================================

# --- Construction ---


def test_base_payment_dates_stored(base):
    assert list(base.payment_dates) == EXPLICIT_DATES


def test_base_end_date_derived_from_max_payment_date(base):
    assert base.end_date == dt.date(2026, 12, 31)


def test_base_amounts_stored(base):
    np.testing.assert_array_equal(base.cashflows, CASHFLOWS)


def test_base_collateral_currency_defaults_to_currency(base):
    assert base.collateral_currency == CURRENCY


def test_base_collateral_currency_explicit():
    schedule = CashFlowSchedule(
        start_date=START,
        payment_dates=EXPLICIT_DATES,
        cashflows=CASHFLOWS,
        currency=Currency.USD,
        daycount=DAYCOUNT,
        collateral_currency=Currency.EUR,
    )
    assert schedule.collateral_currency == Currency.EUR


# --- Validation ---


def test_base_amounts_length_mismatch_raises():
    with pytest.raises(ValueError):
        CashFlowSchedule(
            start_date=START,
            payment_dates=EXPLICIT_DATES,
            cashflows=np.ones(100),
            currency=CURRENCY,
            daycount=DAYCOUNT,
        )


# --- Year fractions ---


def test_base_payment_yearfracs_length(base):
    assert len(base.payment_yearfracs) == len(EXPLICIT_DATES)


def test_base_accrual_yearfracs_length(base):
    assert len(base.accrual_yearfracs) == len(EXPLICIT_DATES)


def test_base_first_payment_yearfrac(base):
    # 2026-01-01 to 2026-03-31 = 89 days / 360
    assert base.payment_yearfracs[0] == pytest.approx(89 / 360)


def test_base_first_accrual_yearfrac(base):
    # 2026-01-01 to 2026-03-31 = 89 days / 360
    assert base.accrual_yearfracs[0] == pytest.approx(89 / 360)


def test_base_accrual_yearfracs_equal_payment_yearfracs_when_no_accrual_dates_passed(
    base,
):
    # When accrual_end_dates is not supplied it defaults to payment_dates,
    # so both yearfrac arrays must be identical.
    np.testing.assert_array_equal(base.accrual_yearfracs, base.payment_yearfracs)


def test_base_accrual_yearfracs_differ_from_payment_yearfracs_when_dates_differ(
    base_with_accrual_dates,
):
    assert not np.allclose(
        base_with_accrual_dates.accrual_yearfracs,
        base_with_accrual_dates.payment_yearfracs,
    )


def test_base_payment_yearfracs_larger_than_accrual_when_payment_dates_later(
    base_with_accrual_dates,
):
    assert all(
        p > a
        for p, a in zip(
            base_with_accrual_dates.payment_yearfracs,
            base_with_accrual_dates.accrual_yearfracs,
        )
    )


# --- DataFrame ---


def test_base_dataframe_shape(base):
    assert base.to_dataframe().shape == (4, 4)


def test_base_dataframe_columns(base):
    assert list(base.to_dataframe().columns) == [
        "Payment Date",
        "Accrual Yearfrac",
        "Payment Yearfrac",
        "Cashflow",
    ]


# --- No frequency-specific attributes ---


def test_base_has_no_frequency_attr(base):
    assert not hasattr(base, "frequency")


def test_base_has_no_dateroll_attr(base):
    assert not hasattr(base, "dateroll")


def test_base_has_no_dayroll_attr(base):
    assert not hasattr(base, "dayroll")


# ===========================================================================
# PeriodicCashFlowSchedule — accrual_end_dates
# ===========================================================================

# accrual_end_dates must be the raw (unrolled) calendar period ends.


def test_accrual_end_dates_count(periodic):
    assert len(periodic.accrual_end_dates) == 4


def test_accrual_end_dates_are_raw_calendar_dates(periodic):
    assert list(periodic.accrual_end_dates) == EXPECTED_ACCRUAL_END_DATES


def test_accrual_end_dates_are_sorted(periodic):
    dates = periodic.accrual_end_dates
    assert all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1))


def test_accrual_end_dates_unaffected_by_lag(periodic_with_lag):
    """accrual_end_dates must not change when a payment lag is applied."""
    expected_raw = [
        dt.date(2027, 3, 31),
        dt.date(2027, 6, 30),
        dt.date(2027, 9, 30),
        dt.date(2027, 12, 31),
    ]
    assert list(periodic_with_lag.accrual_end_dates) == expected_raw


def test_accrual_end_dates_unaffected_by_dateroll(periodic_weekend_roll):
    """
    Even when the raw end falls on a weekend, accrual_end_dates stores the
    calendar date, not the rolled one.
    """
    # 2026-05-31 is a Sunday and must appear as-is in accrual_end_dates
    assert dt.date(2026, 5, 31) in list(periodic_weekend_roll.accrual_end_dates)


# ===========================================================================
# PeriodicCashFlowSchedule — payment_dates (rolled + lagged)
# ===========================================================================


def test_payment_dates_count(periodic):
    assert len(periodic.payment_dates) == 4


def test_payment_dates_equal_rolled_accrual_ends_when_no_lag(periodic):
    """With lag=0 and weekday accrual ends, payment_dates == accrual_end_dates."""
    assert list(periodic.payment_dates) == EXPECTED_PAYMENT_DATES_NO_LAG


def test_payment_dates_are_sorted(periodic):
    dates = periodic.payment_dates
    assert all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1))


def test_payment_dates_differ_from_accrual_end_dates_with_lag(periodic_with_lag):
    """All payment dates must be strictly after their accrual end dates."""
    for accrual, payment in zip(
        periodic_with_lag.accrual_end_dates, periodic_with_lag.payment_dates
    ):
        assert payment > accrual


def test_payment_dates_lag_2_q1_2027(periodic_with_lag):
    # 2027-03-31 (Wednesday) +2 BD lands on 2027-04-02 (Friday)
    assert periodic_with_lag.payment_dates[0] == dt.date(2027, 4, 2)


def test_payment_dates_lag_2_q3_2027(periodic_with_lag):
    # 2027-09-30 (Thursday) +2 BD lands on 2027-10-04 (Monday, skips weekend)
    assert periodic_with_lag.payment_dates[2] == dt.date(2027, 10, 4)


def test_payment_dates_lag_2_q4_2027(periodic_with_lag):
    # 2027-12-31 (Friday) +2 BD lands on 2028-01-04 (Thursday, skips Sat/Sun)
    assert periodic_with_lag.payment_dates[3] == dt.date(2028, 1, 4)


def test_payment_date_rolls_weekend_to_preceding_business_day(periodic_weekend_roll):
    """
    2026-05-31 (Sunday) under MODIFIED_FOLLOWING rolls back to 2026-05-29
    (Friday) because the following BD (2026-06-01) crosses into a new month.
    """
    assert dt.date(2026, 5, 29) in list(periodic_weekend_roll.payment_dates)


def test_payment_dates_are_business_days(periodic_with_lag):
    for d in periodic_with_lag.payment_dates:
        assert d.weekday() < 5, f"{d} is a weekend"


# ===========================================================================
# PeriodicCashFlowSchedule — payment_lag attribute
# ===========================================================================


def test_payment_lag_defaults_to_zero(periodic):
    assert periodic.payment_lag == 0


def test_payment_lag_stored(periodic_with_lag):
    assert periodic_with_lag.payment_lag == 2


def test_payment_lag_negative_raises():
    with pytest.raises(ValueError):
        PeriodicCashFlowSchedule(
            start_date=START,
            end_date=END,
            frequency=FREQUENCY,
            currency=CURRENCY,
            daycount=DAYCOUNT,
            dateroll=DATEROLL,
            cashflows=CASHFLOWS,
            payment_lag=-1,
        )


# ===========================================================================
# PeriodicCashFlowSchedule — dayroll
# ===========================================================================


def test_dayroll_defaults_to_end_date_day(periodic):
    assert periodic.dayroll == END.day


def test_dayroll_explicit():
    schedule = PeriodicCashFlowSchedule(
        start_date=START,
        end_date=END,
        frequency=FREQUENCY,
        currency=CURRENCY,
        daycount=DAYCOUNT,
        dateroll=DATEROLL,
        cashflows=CASHFLOWS,
        dayroll=16,
    )
    assert schedule.dayroll == 16


def test_dayroll_exceeds_31_raises():
    with pytest.raises(ValueError):
        PeriodicCashFlowSchedule(
            start_date=START,
            end_date=END,
            frequency=FREQUENCY,
            currency=CURRENCY,
            daycount=DAYCOUNT,
            dateroll=DATEROLL,
            cashflows=CASHFLOWS,
            dayroll=32,
        )


# ===========================================================================
# PeriodicCashFlowSchedule — properties
# ===========================================================================


def test_frequency_property(periodic):
    assert periodic.frequency == FREQUENCY


def test_dateroll_property(periodic):
    assert periodic.dateroll == DATEROLL


# ===========================================================================
# PeriodicCashFlowSchedule — year fractions
# ===========================================================================


def test_periodic_payment_yearfracs_length(periodic):
    assert len(periodic.payment_yearfracs) == 4


def test_periodic_accrual_yearfracs_length(periodic):
    assert len(periodic.accrual_yearfracs) == 4


def test_periodic_first_payment_yearfrac(periodic):
    # Payment date equals accrual end here (no lag, weekday), so same as accrual.
    # 2026-01-01 to 2026-03-31 = 89 days / 360
    assert periodic.payment_yearfracs[0] == pytest.approx(89 / 360)


def test_periodic_first_accrual_yearfrac(periodic):
    # 2026-01-01 to 2026-03-31 = 89 days / 360
    assert periodic.accrual_yearfracs[0] == pytest.approx(89 / 360)


def test_periodic_accrual_yearfracs_equal_payment_yearfracs_when_no_lag(periodic):
    # With lag=0 and weekday accrual ends, payment dates == accrual end dates,
    # so both yearfrac arrays must be identical.
    np.testing.assert_array_equal(
        periodic.accrual_yearfracs, periodic.payment_yearfracs
    )


def test_periodic_accrual_yearfracs_differ_from_payment_yearfracs_with_lag(
    periodic_with_lag,
):
    # Payment dates are pushed past accrual ends by the lag, so payment
    # yearfracs must be strictly larger than accrual yearfracs for every period.
    assert all(
        p > a
        for p, a in zip(
            periodic_with_lag.payment_yearfracs, periodic_with_lag.accrual_yearfracs
        )
    )


def test_periodic_accrual_yearfracs_use_accrual_dates_not_payment_dates(
    periodic_with_lag,
):
    """
    Accrual yearfracs must be computed from accrual_end_dates. If payment_dates
    were used instead, the Q4 2027 fraction would bleed into 2028 and differ
    measurably from the raw 89-day Q1 figure.
    """
    # Q1 2027: 2027-01-01 to 2027-03-31 = 89 days / 360
    assert periodic_with_lag.accrual_yearfracs[0] == pytest.approx(89 / 360)


def test_periodic_payment_yearfracs_reflect_lagged_dates(periodic_with_lag):
    # Q1 2027: 2027-01-01 to 2027-04-02 (lagged payment) = 91 days / 360
    assert periodic_with_lag.payment_yearfracs[0] == pytest.approx(91 / 360)


# ===========================================================================
# PeriodicCashFlowSchedule — inherited base behaviour
# ===========================================================================


def test_periodic_amounts_mismatch_raises():
    with pytest.raises(ValueError):
        PeriodicCashFlowSchedule(
            start_date=START,
            end_date=END,
            frequency=FREQUENCY,
            currency=CURRENCY,
            daycount=DAYCOUNT,
            dateroll=DATEROLL,
            cashflows=np.ones(100),
        )


def test_periodic_dataframe_shape(periodic):
    assert periodic.to_dataframe().shape == (4, 4)


def test_periodic_dataframe_columns(periodic):
    assert list(periodic.to_dataframe().columns) == [
        "Payment Date",
        "Accrual Yearfrac",
        "Payment Yearfrac",
        "Cashflow",
    ]


def test_periodic_collateral_currency_defaults_to_currency(periodic):
    assert periodic.collateral_currency == CURRENCY


def test_periodic_is_instance_of_base(periodic):
    assert isinstance(periodic, CashFlowSchedule)
