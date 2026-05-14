import pytest
import datetime as dt
import numpy as np
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.time.daycount import Daycount
from qp.time.dateroll import Dateroll
from qp.utils.maps.currencies import Currency

START = dt.date(2026, 1, 1)
END = dt.date(2026, 12, 31)
FREQUENCY = "quarterly"
CURRENCY = Currency.USD
DAYCOUNT = Daycount.ACT_360
DATEROLL = Dateroll.MODIFIED_FOLLOWING
DAYROLL = None
AMOUNTS = np.ones(4)

# --- Date Generation ---


def test_correct_number_of_dates():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert len(schedule.payment_dates) == 4


def test_first_payment_date():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert schedule.payment_dates[0] == dt.date(2026, 3, 31)


def test_last_payment_date():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert schedule.payment_dates[-1] == dt.date(2026, 12, 31)


def test_penultimate_payment_date():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert schedule.payment_dates[-2] == dt.date(2026, 9, 30)


# --- Yearfracs ---


def test_yearfracs_length():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert len(schedule.yearfracs) == 4


def test_first_yearfrac():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert schedule.yearfracs[0] == pytest.approx(0.247222222)


# --- Validation ---


def test_amounts_mismatch():
    with pytest.raises(ValueError):
        CashFlowSchedule(
            START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, np.ones(100)
        )  # wrong length


# --- DataFrame ---


def test_dataframe_shape():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    df = schedule.to_dataframe()
    assert df.shape == (4, 3)  # 4 rows, 3 cols


def test_dataframe_columns():
    schedule = CashFlowSchedule(
        START, END, FREQUENCY, CURRENCY, DAYCOUNT, DATEROLL, AMOUNTS, DAYROLL
    )
    assert list(schedule.to_dataframe().columns) == ["Payment Date", "DCF", "Cashflow"]
