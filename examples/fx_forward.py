"""
FX Forward pricing example.

Prices a EUR/AUD forward using two USD-denominated FX curves.
Cross-rate derived as F(AUD/EUR) = F(USD/EUR) / F(USD/AUD).
Undiscounted payoff converted to USD, then discounted via DCFPricer.
"""

import datetime as dt

from qp.curves.fx_curve import FXCurve
from qp.curves.ir_curve import IRCurve
from qp.instruments.fx.fx_forward import FXForward
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.price_and_risk.discount_cashflows import DCFPricer, PricingSpec
from qp.time.date.daycount import Daycount
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.buysell import BuySell

VALUATION_DATE = dt.date(2026, 6, 1)

eur_curve = FXCurve(
    at_date=VALUATION_DATE,
    daycount=Daycount.ACT_360,
    currency_1=Currency.EUR,
    currency_2=Currency.USD,
    fx_rates=[1.08, 1.082, 1.085],
    tenors=[0.0, 1.0, 2.0],
)

aud_curve = FXCurve(
    at_date=VALUATION_DATE,
    daycount=Daycount.ACT_360,
    currency_1=Currency.AUD,
    currency_2=Currency.USD,
    fx_rates=[0.65, 0.648, 0.645],
    tenors=[0.0, 1.0, 2.0],
)

ir_curve = IRCurve(
    at_date=VALUATION_DATE,
    daycount=Daycount.ACT_360,
    currency=Currency.USD,
    curve_name="USD_SOFR",
    tenors=[0.0, 1.0, 2.0],
    discount_factors=[1.0, 0.9505, 0.9048],
)

# Buy 1M EUR vs AUD, struck at 1.65 AUD/EUR
forward = FXForward(
    buy_sell=BuySell.BUY,
    base_ccy=Currency.EUR,
    term_ccy=Currency.AUD,
    notional1=1_000_000,
    notional2=1_650_000,
    maturity_date=dt.date(2027, 6, 3),
)

model = FXForwardModel(
    valuation_date=VALUATION_DATE,
    base_fx_curve=eur_curve,
    term_fx_curve=aud_curve,
)

spec = PricingSpec(model=model, instrument=forward, discount_curve=ir_curve)
result = DCFPricer(spec).discount_cashflows()

schedule = model.price(forward)
fwd_rate = eur_curve.get_rates(1.0) / aud_curve.get_rates(1.0)
print(f"Forward rate:        {fwd_rate:.4f} AUD/EUR")
print(f"Strike:              {forward.strike:.4f} AUD/EUR")
print(f"Undiscounted payoff: USD {schedule.cashflows[0]:,.2f}")
print(f"PV:                  USD {result[0].value:,.2f}")
