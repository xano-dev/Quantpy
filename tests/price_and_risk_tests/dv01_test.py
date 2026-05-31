import datetime as dt
import pytest
import numpy as np

from qp.price_and_risk.greeks import Greeks
from qp.price_and_risk.discount_cashflows import DCFPricer
from qp.price_and_risk.pricing_spec import PricingSpec
from qp.models.rates.irs_model import IRSModel
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.instruments.fx.fx_forward import FXForward
from qp.curves.ir_curve import IRCurve
from qp.curves.fx_curve import FXCurve
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.time.date.daycount import Daycount, yearfrac
from qp.time.date.dateroll import Dateroll
from qp.time.cashflows.cashflow_schedule import PeriodicCashFlowSchedule

VALUATION_DATE = dt.date(2025, 1, 1)
START_DATE = dt.date(2025, 1, 3)
END_DATE = dt.date(2026, 1, 3)

NOTIONAL = 1_000_000
C = 0.05
R = 0.03
SHOCK = 0.0001


def make_flat_ir_curve(rate: float) -> IRCurve:
    return IRCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_365,
        currency=Currency.USD,
        curve_name="USD_SOFR",
        tenors=[0.0, 0.5, 1.0, 2.0, 5.0],
        interest_rates=[rate] * 5,
    )


def make_fixed_leg_irs() -> IRS:
    return IRS(
        leg_one=IRFixedLeg(
            currency=Currency.USD,
            notional=NOTIONAL,
            start_date=START_DATE,
            end_date=END_DATE,
            payment_frequency=Frequency.ANNUAL,
            collateral_currency=Currency.USD,
            daycount=Daycount.ACT_365,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.PAY,
            fixed_rate=C,
        ),
        leg_two=None,
    )


def test_dv01_fixed_flat():

    upward_fixed_leg = -(
        NOTIONAL
        * C
        * yearfrac(START_DATE, END_DATE, Daycount.ACT_365)
        * np.exp(
            -(R + SHOCK)
            * yearfrac(
                VALUATION_DATE, END_DATE + dt.timedelta(days=2), Daycount.ACT_365
            )
        )
    )
    downward_fixed_leg = -(
        NOTIONAL
        * C
        * yearfrac(START_DATE, END_DATE, Daycount.ACT_365)
        * np.exp(
            -(R - SHOCK)
            * yearfrac(
                VALUATION_DATE, END_DATE + dt.timedelta(days=2), Daycount.ACT_365
            )
        )
    )
    expected_dv01 = 0.0001 * (upward_fixed_leg - downward_fixed_leg) / (2 * SHOCK)

    curve = make_flat_ir_curve(R)
    instrument = make_fixed_leg_irs()
    model = IRSModel(valuation_date=VALUATION_DATE, leg_one_curve=curve)
    pricing_spec = PricingSpec(
        model=model,
        instrument=instrument,
        discount_curve=curve,
        fx_curves=None,
    )
    pricer = DCFPricer(pricing_spec)
    greeks = Greeks(pricing_spec=pricing_spec, pricer=pricer)

    dv01 = greeks.parallel_dv01(shock=SHOCK)

    assert dv01 == pytest.approx(expected_dv01, rel=1e-4)


def make_floating_leg_irs() -> IRS:
    return IRS(
        leg_one=IRFloatingLeg(
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
            spread=0.0,
        ),
        leg_two=None,
    )


def test_dv01_floating_leg_larger_than_fixed():
    # floating leg DV01 should be larger than fixed in magnitude:
    # both discounting AND forward rate projection are sensitive to rate moves
    curve = make_flat_ir_curve(R)
    fixed_instrument = make_fixed_leg_irs()
    floating_instrument = make_floating_leg_irs()

    fixed_model = IRSModel(valuation_date=VALUATION_DATE, leg_one_curve=curve)
    floating_model = IRSModel(valuation_date=VALUATION_DATE, leg_one_curve=curve)

    fixed_spec = PricingSpec(
        model=fixed_model,
        instrument=fixed_instrument,
        discount_curve=curve,
        fx_curves=None,
    )
    floating_spec = PricingSpec(
        model=floating_model,
        instrument=floating_instrument,
        discount_curve=curve,
        fx_curves=None,
    )

    fixed_dv01 = Greeks(
        pricing_spec=fixed_spec, pricer=DCFPricer(fixed_spec)
    ).parallel_dv01(shock=SHOCK)
    floating_dv01 = Greeks(
        pricing_spec=floating_spec, pricer=DCFPricer(floating_spec)
    ).parallel_dv01(shock=SHOCK)

    assert abs(floating_dv01) > abs(fixed_dv01)


def make_float_irs() -> IRS:
    return IRS(
        leg_one=None,
        leg_two=IRFloatingLeg(
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
            spread=0.0,
        ),
    )


def test_dv01_float_leg():
    curve = make_flat_ir_curve(R)
    up_curve = curve.shock_curve(SHOCK)
    down_curve = curve.shock_curve(-SHOCK)

    pv_float_up = NOTIONAL * (
        up_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, START_DATE, Daycount.ACT_365)
        )
        - up_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, END_DATE, Daycount.ACT_365)
        )
    )

    pv_float_down = NOTIONAL * (
        down_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, START_DATE, Daycount.ACT_365)
        )
        - down_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, END_DATE, Daycount.ACT_365)
        )
    )

    expected_dv01 = 0.0001 * (pv_float_up - pv_float_down) / (2 * SHOCK)

    instrument = make_float_irs()

    model = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=curve, leg_two_curve=curve
    )
    pricing_spec = PricingSpec(
        model=model, instrument=instrument, discount_curve=curve, fx_curves=None
    )

    greeks = Greeks(pricing_spec=pricing_spec, pricer=DCFPricer(pricing_spec))

    dv01 = greeks.parallel_dv01(shock=SHOCK)

    assert abs(dv01) == pytest.approx(expected_dv01, abs=0.6)


def make_irs() -> IRS:
    return IRS(
        leg_one=IRFixedLeg(
            currency=Currency.USD,
            notional=NOTIONAL,
            start_date=START_DATE,
            end_date=END_DATE,
            payment_frequency=Frequency.ANNUAL,
            collateral_currency=Currency.USD,
            daycount=Daycount.ACT_365,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.PAY,
            fixed_rate=C,
        ),
        leg_two=IRFloatingLeg(
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
            spread=0.0,
        ),
    )


def test_dv01_additivity():

    upward_fixed_leg = -(
        NOTIONAL
        * C
        * yearfrac(START_DATE, END_DATE, Daycount.ACT_365)
        * np.exp(
            -(R + SHOCK)
            * yearfrac(
                VALUATION_DATE, END_DATE + dt.timedelta(days=2), Daycount.ACT_365
            )
        )
    )
    downward_fixed_leg = -(
        NOTIONAL
        * C
        * yearfrac(START_DATE, END_DATE, Daycount.ACT_365)
        * np.exp(
            -(R - SHOCK)
            * yearfrac(
                VALUATION_DATE, END_DATE + dt.timedelta(days=2), Daycount.ACT_365
            )
        )
    )
    expected_fixed_dv01 = 0.0001 * (upward_fixed_leg - downward_fixed_leg) / (2 * SHOCK)

    curve = make_flat_ir_curve(R)
    up_curve = curve.shock_curve(SHOCK)
    down_curve = curve.shock_curve(-SHOCK)

    pv_float_up = NOTIONAL * (
        up_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, START_DATE, Daycount.ACT_365)
        )
        - up_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, END_DATE, Daycount.ACT_365)
        )
    )

    pv_float_down = NOTIONAL * (
        down_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, START_DATE, Daycount.ACT_365)
        )
        - down_curve.get_discount_factors(
            yearfrac(VALUATION_DATE, END_DATE, Daycount.ACT_365)
        )
    )

    expected_float_dv01 = 0.0001 * (pv_float_up - pv_float_down) / (2 * SHOCK)

    expected_dv01 = expected_fixed_dv01 + expected_float_dv01

    instrument = make_irs()

    model = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=None, leg_two_curve=curve
    )

    pricing_spec = PricingSpec(
        model=model, instrument=instrument, discount_curve=curve, fx_curves=None
    )

    greeks = Greeks(pricing_spec=pricing_spec, pricer=DCFPricer(pricing_spec))

    dv01 = greeks.parallel_dv01(shock=SHOCK)

    assert dv01 == pytest.approx(expected_dv01, abs=0.6)
