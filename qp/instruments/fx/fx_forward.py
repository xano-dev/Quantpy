import datetime as dt
from typing import Literal

from qp.utils.maps.currencies import Currency


class FXForward:
    """Python representation of an FX Forward. Strike is computed from notionals.

    -   Strike is computed as notional2/notional1 for Buy,
        and notional1/notional2 for Sell, consistent with
        quoting all FX rates as foreign/USD.

    Args:
        buy_sell: buy/sell ccy1
        ccy1: first currency of the FX Forward
        ccy2: second currency of the FX Forward
        notional1: notional of ccy1
        notional2: notional of ccy2
        maturity_date: maturity date of the FX Forward
        collateral_ccy: collateral currency (if any) - default discounting is USD SOFR
    Example:
        >>> forward = FXForward(
        ...     buy_sell="Buy",
        ...     ccy1=Currency.EUR,
        ...     ccy2=Currency.USD,
        ...     notional1=1_000_000,
        ...     notional2=500_000,
        ...     maturity_date=dt.date(2028, 5, 10),
        ...     collateral_ccy=Currency.EUR
        ... )
    """

    def __init__(
        self,
        buy_sell: Literal["Buy", "Sell"],
        ccy1: Currency,
        ccy2: Currency,
        notional1: float,
        notional2: float,
        maturity_date: dt.date,
        collateral_ccy: Currency | None = Currency.USD,
    ):

        self._buy_sell = buy_sell
        self._ccy1 = ccy1
        self._ccy2 = ccy2
        self._notional1 = notional1
        self._notional2 = notional2
        self._maturity_date = maturity_date
        self._collateral_ccy = collateral_ccy

    @property
    def buy_sell(self):
        return self._buy_sell

    @property
    def ccy1(self):
        return self._ccy1

    @property
    def ccy2(self):
        return self._ccy2

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
        return (
            self._notional2 / self._notional1
            if self._buy_sell == "Buy"
            else self._notional1 / self._notional2
        )
