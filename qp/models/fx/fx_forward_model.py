from qp.instruments.fx.fx_forward import FXForward
from qp.curves.fx_curve import FXCurve
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.utils.maps.currencies import Currency
from qp.time.daycount import Daycount
from qp.utils.maps.buysell import BuySell
from qp.utils.maps.currency_daycount import CURRENCY_DAYCOUNT

import datetime as dt


class FXForwardModel:

    def __init__(
        self, valuation_date: dt.date, base_fx_curve: FXCurve, term_fx_curve: FXCurve
    ):
        self._valuation_date = valuation_date
        self._base_fx_curve = base_fx_curve
        self._term_fx_curve = term_fx_curve

        self._check_errors()

    def _get_forward_fx(self, fx_forward: FXForward):
        base_fwd_fx = (
            1
            if fx_forward.base_ccy == Currency.USD
            else self._base_fx_curve.get_rates(fx_forward.maturity_date)
        )  # USD / base
        term_fwd_fx = (
            1
            if fx_forward.term_ccy == Currency.USD
            else self._term_fx_curve.get_rates(fx_forward.maturity_date)
        )  # USD / term

        fwd_fx = base_fwd_fx / term_fwd_fx  # fwd fx in term / base

        return fwd_fx, term_fwd_fx

    def _check_errors(self):
        if (
            self._base_fx_curve.currency_2 != Currency.USD
            or self._term_fx_curve.currency_2 != Currency.USD
        ):
            raise ValueError("base curve and term curve must be in USD / currency")

        if (
            self._base_fx_curve.at_date != self._valuation_date
            or self._term_fx_curve.at_date != self._valuation_date
        ):
            raise ValueError(
                f"base curve (at_date {self._base_fx_curve.at_date}) or term curve (at_date {self._term_fx_curve.at_date}) is not as at valuation date {self._valuation_date}"
            )

    def price(self, fx_forward: FXForward) -> CashFlowSchedule:
        """
        Computes the undiscounted USD payoff of an FX Forward.

        All FX rates are quoted as USD/foreign (USD per unit of foreign currency).
        The cross forward rate is derived via: F(term/base) = F(USD/base) / F(USD/term).
        Payoff is converted to USD using the term currency's forward FX rate.

        Data is seeded in `qp/data/fx_curves/seed_fx_curves.py`

        Example (Buy EUR/AUD):
            >>> forward = FXForward(
            ...     buy_sell=BuySell.BUY,
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

        fwd_fx, term_fwd_fx = self._get_forward_fx(fx_forward)

        fwd_points = (
            fwd_fx - fx_forward.strike
            if fx_forward.buy_sell == BuySell.BUY
            else fx_forward.strike - fwd_fx
        )

        payoff = fx_forward.notional1 * fwd_points * term_fwd_fx  # payoff in USD

        return CashFlowSchedule(
            self._valuation_date,
            [fx_forward.maturity_date],
            [payoff],
            Currency.USD,
            CURRENCY_DAYCOUNT[fx_forward.collateral_ccy],
            fx_forward.collateral_ccy,
        )
