from qp.instruments.fx.fx_forward import FXForward
from qp.curves.fx_curve import FXCurve
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.utils.maps.currencies import Currency
from qp.data.get_fx_curve import get_fx_curve
from qp.time.daycount import Daycount

import datetime as dt


def price_fx_forward(
    fx_forward: FXForward,
    valuation_date: dt.date,
) -> tuple:
    """
    Computes the undiscounted USD payoff of an FX Forward.

    All FX rates are quoted as USD/foreign (USD per unit of foreign currency).
    The cross forward rate is derived via: F(term/base) = F(USD/base) / F(USD/term).
    Payoff is converted to USD using the term currency's forward FX rate.

    Data is seeded in `qp/data/fx_curves/seed_fx_curves.py`

    Example (Buy EUR/AUD):
        >>> forward = FXForward(
        ...     buy_sell="Buy",
        ...     base_ccy=Currency.EUR,
        ...     term_ccy=Currency.AUD,
        ...     notional1=1_000_000,
        ...     notional2=500_000,
        ...     maturity_date=dt.date(2028, 5, 10),
        ... )

        >>> N1                 = 1,000,000 EUR
        >>> Strike             = N2 / N1                    = 0.5000 AUD/EUR
        >>> F(USD/EUR) at 2Y   ≈ 1.1270 USD/EUR             (from EUR FX curve)
        >>> F(USD/AUD) at 2Y   ≈ 0.7270 USD/AUD             (from AUD FX curve)
        >>> F(AUD/EUR) at 2Y   = 1.1270 / 0.7270            ≈ 1.5502 AUD/EUR
        >>> Fwd points         = F - K                      = 1.5502 - 0.5000 = 1.0502 AUD/EUR
        >>> Payoff (AUD)       = N1 * fwd_points            = 1,000,000 * 1.0502 = 1,050,200 AUD
        >>> Payoff (USD)       = payoff_AUD * F(USD/AUD)    = 1,050,200 * 0.7270 ≈ 763,495 USD

    """

    def _compute_forward_fx():
        base_fwd_fx = (
            1
            if fx_forward.base_ccy == Currency.USD
            else base_fx_curve.get_rates(fx_forward.maturity_date)
        )  # USD / base
        term_fwd_fx = (
            1
            if fx_forward.term_ccy == Currency.USD
            else term_fx_curve.get_rates(fx_forward.maturity_date)
        )  # USD / term

        fwd_fx = base_fwd_fx / term_fwd_fx  # fwd fx in term / base

        return fwd_fx, term_fwd_fx

    def _generate_fx_curve(currency: Currency):
        fx_rates, tenors, daycount = get_fx_curve(currency, valuation_date)

        fx_curve: FXCurve = FXCurve(
            valuation_date,
            daycount,
            currency,
            Currency.USD,
            fx_rates,
            tenors,
        )

        return fx_curve

    base_fx_curve = (
        1
        if fx_forward.base_ccy == Currency.USD
        else _generate_fx_curve(fx_forward.base_ccy)
    )

    term_fx_curve = (
        1
        if fx_forward.term_ccy == Currency.USD
        else _generate_fx_curve(fx_forward.term_ccy)
    )

    fwd_fx, term_fwd_fx = (
        _compute_forward_fx()
    )  # fwd fx in term / base, usd / base, and usd / term

    fwd_points = (
        fwd_fx - fx_forward.strike
        if fx_forward.buy_sell == "Buy"
        else fx_forward.strike - fwd_fx
    )

    payoff = fx_forward.notional1 * fwd_points * term_fwd_fx  # payoff in USD

    return fx_forward, CashFlowSchedule.from_dates(
        valuation_date,
        [fx_forward.maturity_date],
        payoff,
        Currency.USD,
        Daycount.ACT_360,
    )
