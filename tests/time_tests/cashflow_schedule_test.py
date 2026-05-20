import pytest
import datetime as dt
import numpy as np

from qp.time.cashflows.cashflow_schedule import (
    CashFlowSchedule,
    PeriodicCashFlowSchedule,
)
from qp.time.daycount import Daycount
from qp.time.dateroll import Dateroll
from qp.utils.maps.currencies import Currency

# ---------------------------------------------------------------------------
# Fixtures
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


@pytest.fixture
def periodic():
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
def base():
    return CashFlowSchedule(
        start_date=START,
        payment_dates=EXPLICIT_DATES,
        cashflows=CASHFLOWS,
        currency=CURRENCY,
        daycount=DAYCOUNT,
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


def test_base_yearfracs_length(base):
    assert len(base.yearfracs) == len(EXPLICIT_DATES)


def test_base_first_yearfrac(base):
    assert base.yearfracs[0] == pytest.approx(0.247222222)


# --- DataFrame ---


def test_base_dataframe_shape(base):
    assert base.to_dataframe().shape == (4, 3)


def test_base_dataframe_columns(base):
    assert list(base.to_dataframe().columns) == ["Payment Date", "DCF", "Cashflow"]


# --- No frequency-specific attributes ---


def test_base_has_no_frequency_attr(base):
    assert not hasattr(base, "frequency")


def test_base_has_no_dateroll_attr(base):
    assert not hasattr(base, "dateroll")


def test_base_has_no_dayroll_attr(base):
    assert not hasattr(base, "dayroll")


# ===========================================================================
# PeriodicCashFlowSchedule
# ===========================================================================

# --- Date generation ---


def test_correct_number_of_dates(periodic):
    assert len(periodic.payment_dates) == 4


def test_first_payment_date(periodic):
    assert periodic.payment_dates[0] == dt.date(2026, 3, 31)


def test_last_payment_date(periodic):
    assert periodic.payment_dates[-1] == dt.date(2026, 12, 31)


def test_penultimate_payment_date(periodic):
    assert periodic.payment_dates[-2] == dt.date(2026, 9, 30)


def test_payment_dates_are_sorted(periodic):
    dates = periodic.payment_dates
    assert all(dates[i] <= dates[i + 1] for i in range(len(dates) - 1))


# --- Dayroll ---


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


# --- Properties ---


def test_frequency_property(periodic):
    assert periodic.frequency == FREQUENCY


def test_dateroll_property(periodic):
    assert periodic.dateroll == DATEROLL


# --- Inherited base behaviour ---


def test_periodic_yearfracs_length(periodic):
    assert len(periodic.yearfracs) == 4


def test_periodic_first_yearfrac(periodic):
    assert periodic.yearfracs[0] == pytest.approx(0.247222222)


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
    assert periodic.to_dataframe().shape == (4, 3)


def test_periodic_dataframe_columns(periodic):
    assert list(periodic.to_dataframe().columns) == ["Payment Date", "DCF", "Cashflow"]


def test_periodic_collateral_currency_defaults_to_currency(periodic):
    assert periodic.collateral_currency == CURRENCY


def test_periodic_is_instance_of_base(periodic):
    assert isinstance(periodic, CashFlowSchedule)
