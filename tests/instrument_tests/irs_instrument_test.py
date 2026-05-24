import datetime as dt
import pytest

from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.utils.maps.rates.leg_type import LegType
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll

START_DATE = dt.date(2026, 6, 3)
END_DATE = dt.date(2028, 6, 3)
NOTIONAL = 10_000_000
FIXED_RATE = 0.05


def make_fixed_leg(**kwargs):
    defaults = dict(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE,
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
        end_date=END_DATE,
        payment_frequency=Frequency.QUARTERLY,
        collateral_currency=Currency.USD,
        daycount=Daycount.ACT_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.RECEIVE,
        index=FloatingIndex.SOFR,
    )
    return IRFloatingLeg(**{**defaults, **kwargs})


# --- IRFixedLeg properties ---


def test_fixed_leg_properties():
    leg = make_fixed_leg()
    assert leg.currency == Currency.USD
    assert leg.notional == NOTIONAL
    assert leg.start_date == START_DATE
    assert leg.end_date == END_DATE
    assert leg.payment_frequency == Frequency.SEMI_ANNUAL
    assert leg.collateral_currency == Currency.USD
    assert leg.daycount == Daycount.THIRTY_360
    assert leg.dateroll == Dateroll.MODIFIED_FOLLOWING
    assert leg.pay_receive == PayReceive.PAY
    assert leg.fixed_rate == FIXED_RATE
    assert leg.leg_type == LegType.FIXED


def test_fixed_leg_dayroll_defaults_to_end_date_day():
    leg = make_fixed_leg()
    assert leg.dayroll == END_DATE.day


def test_fixed_leg_dayroll_override():
    leg = make_fixed_leg(dayroll=15)
    assert leg.dayroll == 15


def test_fixed_leg_payment_lag_defaults_to_zero():
    leg = make_fixed_leg()
    assert leg.payment_lag == 0


def test_fixed_leg_collateral_defaults_to_currency():
    leg = IRFixedLeg(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE,
        payment_frequency=Frequency.SEMI_ANNUAL,
        collateral_currency=Currency.USD,
        daycount=Daycount.THIRTY_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.PAY,
        fixed_rate=FIXED_RATE,
    )
    assert leg.collateral_currency == Currency.USD


def test_fixed_leg_pay_receive_enum_wrapping():
    """String input should be coerced to PayReceive enum."""
    leg = make_fixed_leg(pay_receive="pay")
    assert leg.pay_receive == PayReceive.PAY


# --- IRFloatingLeg properties ---


def test_float_leg_properties():
    leg = make_float_leg()
    assert leg.currency == Currency.USD
    assert leg.notional == NOTIONAL
    assert leg.start_date == START_DATE
    assert leg.end_date == END_DATE
    assert leg.payment_frequency == Frequency.QUARTERLY
    assert leg.index == FloatingIndex.SOFR
    assert leg.spread == 0.0
    assert leg.leg_type == LegType.FLOAT
    assert leg.pay_receive == PayReceive.RECEIVE


def test_float_leg_spread_default():
    leg = make_float_leg()
    assert leg.spread == 0.0


def test_float_leg_spread_override():
    leg = make_float_leg(spread=0.001)
    assert leg.spread == pytest.approx(0.001)


def test_float_leg_lookback_default():
    leg = make_float_leg()
    assert leg.lookback == 30


def test_float_leg_ois_leg_type():
    leg = make_float_leg(leg_type=LegType.OIS)
    assert leg.leg_type == LegType.OIS


def test_float_leg_pay_receive_enum_wrapping():
    """String input should be coerced to PayReceive enum."""
    leg = make_float_leg(pay_receive="receive")
    assert leg.pay_receive == PayReceive.RECEIVE


# --- IRS ---


def test_irs_legs():
    fixed = make_fixed_leg()
    floating = make_float_leg()
    irs = IRS(leg_one=fixed, leg_two=floating)
    assert irs.leg_one is fixed
    assert irs.leg_two is floating


def test_irs_legs_property_returns_both():
    fixed = make_fixed_leg()
    floating = make_float_leg()
    irs = IRS(leg_one=fixed, leg_two=floating)
    assert len(irs.legs) == 2
    assert irs.legs[0] is fixed
    assert irs.legs[1] is floating
