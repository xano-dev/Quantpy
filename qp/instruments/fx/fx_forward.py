import datetime as dt
from typing import Literal

from qp.utils.maps.currencies import Currency
from qp.curves.fx_curve import FXCurve


class FXForward:
    """Python representation of an FX Forward. Strike is computed from notionals.

    -   Strike is computed as notional2/notional1 (term / base) always

    Args:
        buy_sell: buy/sell base_ccy
        base_ccy: first currency of the FX Forward
        term_ccy: second currency of the FX Forward
        notional1: notional of base_ccy
        notional2: notional of term_ccy
        maturity_date: maturity date of the FX Forward
        collateral_ccy: collateral currency (if any) - default discounting is USD SOFR
    Example:
        >>> forward = FXForward(
        ...     buy_sell="Buy",
        ...     base_ccy=Currency.EUR,
        ...     term_ccy=Currency.USD,
        ...     notional1=1_000_000,
        ...     notional2=500_000,
        ...     maturity_date=dt.date(2028, 5, 10),
        ...     collateral_ccy=Currency.EUR
        ... )
    """

    def __init__(
        self,
        buy_sell: Literal["Buy", "Sell"],
        base_ccy: Currency,
        term_ccy: Currency,
        notional1: float,
        notional2: float,
        maturity_date: dt.date,
        collateral_ccy: Currency | None = Currency.USD,
    ):

        self._buy_sell = buy_sell
        self._base_ccy = base_ccy
        self._term_ccy = term_ccy
        self._notional1 = notional1
        self._notional2 = notional2
        self._maturity_date = maturity_date
        self._collateral_ccy = collateral_ccy

    @property
    def buy_sell(self):
        return self._buy_sell

    @property
    def base_ccy(self):
        return self._base_ccy

    @property
    def term_ccy(self):
        return self._term_ccy

    @property
    def notional1(self):
        return self._notional1

    @property
    def notional2(self):
        return self._notional2

    @property
    def maturity_date(self):
        return self._maturity_date

    @property
    def collateral_ccy(self):
        return self._collateral_ccy

    @property
    def strike(self):
        return self._notional2 / self._notional1
