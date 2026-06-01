import datetime as dt
import numpy as np
import pytest

from qp.price_and_risk.greeks import Greeks
from qp.price_and_risk.discount_cashflows import DCFPricer
from qp.price_and_risk.pricing_spec import PricingSpec
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.instruments.fx.fx_forward import FXForward
from qp.curves.ir_curve import IRCurve
from qp.curves.fx_curve import FXCurve
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.buysell import BuySell
from qp.time.date.daycount import Daycount
from qp.time.date.daycount import yearfrac

VALUATION_DATE = dt.date(2025, 1, 1)
MATURITY_DATE = dt.date(2026, 1, 1)

SPOT = 1.10
NOTIONAL = 1_000_000
RATE = 0.05
FX_SHOCK = 0.1
IR_SHOCK = 0.0001
T = yearfrac(
    VALUATION_DATE, MATURITY_DATE, Daycount.ACT_365, Currency.EUR, Currency.USD
)


def make_flat_eur_usd_curve() -> FXCurve:
    return FXCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_365,
        currency_1=Currency.EUR,
        currency_2=Currency.USD,
        fx_rates=[SPOT, SPOT, SPOT],
        tenors=[0.0, 0.5, 1.0],
    )


def make_flat_usd_usd_curve() -> FXCurve:
    return FXCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_365,
        currency_1=Currency.USD,
        currency_2=Currency.USD,
        fx_rates=[1.0, 1.0, 1.0],
        tenors=[0.0, 0.5, 1.0],
    )


def make_flat_ir_curve() -> IRCurve:
    return IRCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_365,
        currency=Currency.USD,
        curve_name="USD_SOFR",
        tenors=[0.0, 0.5, 1.0],
        interest_rates=[RATE, RATE, RATE],
    )


def make_greeks(buy_sell: BuySell) -> Greeks:
    fwd = FXForward(
        buy_sell=buy_sell,
        base_ccy=Currency.EUR,
        term_ccy=Currency.USD,
        notional1=NOTIONAL,
        notional2=NOTIONAL * SPOT,
        maturity_date=MATURITY_DATE,
    )

    model = FXForwardModel(
        valuation_date=VALUATION_DATE,
        base_fx_curve=make_flat_eur_usd_curve(),
        term_fx_curve=make_flat_usd_usd_curve(),
    )

    pricing_spec = PricingSpec(
        model=model,
        instrument=fwd,
        discount_curve=make_flat_ir_curve(),
        fx_curves=None,
    )

    return Greeks(pricing_spec, DCFPricer(pricing_spec))


def test_cross_gamma_long():
    greeks = make_greeks(BuySell.BUY)
    cross_gamma = greeks.cross_gamma(FX_SHOCK, IR_SHOCK)

    expected_cross_gamma = -T * NOTIONAL * np.exp(-0.05)

    assert cross_gamma == pytest.approx(expected_cross_gamma)
