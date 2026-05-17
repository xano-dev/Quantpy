import datetime as dt
from dataclasses import dataclass
from qp.utils.maps.currencies import Currency


@dataclass
class CashFlow:
    """A python object representing a single cashflow"""

    date: dt.date
    currency: Currency
    amount: float
