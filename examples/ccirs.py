"""
Cross-Currency Interest Rate Swap (CCIRS) pricing example.

Prices a 2Y CCIRS: pay 5% EUR fixed semi-annual, receive USD SOFR quarterly.
The EUR fixed leg cashflows are converted to USD via a forward FX curve before
discounting. The USD float leg requires no FX conversion.

fx_curves is a per-leg list — None signals no conversion needed for that leg.
"""

import datetime as dt

from qp.curves.fx_curve import FXCurve
from qp.curves.ir_curve import IRCurve
from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.models.rates.irs_model import IRSModel
from qp.price_and_risk.discount_cashflows import DCFPricer, PricingSpec
from qp.time.date.dateroll import Dateroll
from qp.time.date.daycount import Daycount, yearfrac
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex

VALUATION_DATE = dt.date(2026, 6, 1)
START_DATE = dt.date(2026, 6, 3)
END_DATE = dt.date(2028, 6, 3)
NOTIONAL = 10_000_000

usd_curve = IRCurve(
    at_date=VALUATION_DATE,
    daycount=Daycount.ACT_360,
    currency=Currency.USD,
    curve_name="USD_SOFR",
    tenors=[0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0],
    discount_factors=[1.0, 0.9875, 0.9750, 0.9505, 0.9048, 0.8607, 0.7788],
)

eur_fx = FXCurve(
    at_date=VALUATION_DATE,
    daycount=Daycount.ACT_360,
    currency_1=Currency.EUR,
    currency_2=Currency.USD,
    fx_rates=[1.08, 1.082, 1.085, 1.087],
    tenors=[0.0, 1.0, 2.0, 3.0],
)

ccirs = IRS(
    leg_one=IRFixedLeg(
        currency=Currency.EUR,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE,
        payment_frequency=Frequency.SEMI_ANNUAL,
        collateral_currency=Currency.USD,
        daycount=Daycount.THIRTY_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.PAY,
        fixed_rate=0.05,
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
    ),
)

model = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=usd_curve)

spec = PricingSpec(
    model=model,
    instrument=ccirs,
    discount_curve=usd_curve,
    fx_curves=[eur_fx, None],
)
result = DCFPricer(spec).discount_cashflows()

fixed_schedule, float_schedule = model.price(ccirs)
print("EUR fixed leg cashflows (undiscounted):")
for date, cf in zip(fixed_schedule.payment_dates, fixed_schedule.cashflows):
    print(
        f"  {date}  EUR {cf:,.2f}  (~USD {cf * eur_fx.get_rates(yearfrac(VALUATION_DATE, date, Daycount.ACT_360)):,.2f})"
    )

print("\nUSD float leg cashflows (undiscounted):")
for date, cf in zip(float_schedule.payment_dates, float_schedule.cashflows):
    print(f"  {date}  USD {cf:,.2f}")

print(f"\nPV (discounted): USD {result[0].value:,.2f}")
