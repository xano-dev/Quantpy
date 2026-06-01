import datetime as dt
import pytest

from qp.instruments.rates.ir_cap import IRCap
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll

START_DATE = dt.date(2025, 1, 1)
END_DATE = dt.date(2026, 1, 1)
NOTIONAL = 1_000_000
STRIKE = 0.05


def make_cap(start_date=START_DATE, end_date=END_DATE) -> IRCap:
    return IRCap(
        currency=Currency.EUR,
        notional=NOTIONAL,
        start_date=start_date,
        end_date=end_date,
        payment_frequency=Frequency.QUARTERLY,
        collateral_currency=Currency.EUR,
        daycount=Daycount.ACT_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.RECEIVE,
        index=FloatingIndex.EURIBOR_3M,
        strike=STRIKE,
    )


# ---- Construction ----


def test_construction_passes():
    cap = make_cap()
    assert cap.notional == NOTIONAL
    assert cap.strike == STRIKE
    assert cap.start_date == START_DATE
    assert cap.end_date == END_DATE


def test_start_date_equals_end_date_raises():
    with pytest.raises(ValueError):
        make_cap(start_date=START_DATE, end_date=START_DATE)


def test_start_date_after_end_date_raises():
    with pytest.raises(ValueError):
        make_cap(start_date=END_DATE, end_date=START_DATE)
