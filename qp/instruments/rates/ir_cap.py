import datetime as dt

from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.utils.maps.general.payreceive import PayReceive
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll


class IRCap:

    def __init__(
        self,
        currency: Currency,
        notional: float,
        start_date: dt.date,
        end_date: dt.date,
        payment_frequency: Frequency,
        collateral_currency: Currency,
        daycount: Daycount,
        dateroll: Dateroll,
        pay_receive: PayReceive,  # RECEIVE = long cap (you receive payoffs)
        index: FloatingIndex,
        strike: float,
        payment_lag: int = 0,
        dayroll: int | None = None,
    ):
        self._currency = currency
        self._notional = notional
        self._start_date = start_date
        self._end_date = end_date
        self._payment_frequency = payment_frequency
        self._collateral_currency = collateral_currency
        self._daycount = daycount
        self._dateroll = dateroll
        self._pay_receive = PayReceive(pay_receive)
        self._index = index
        self._strike = strike
        self._payment_lag = payment_lag
        self._dayroll = dayroll if dayroll is not None else end_date.day

        self._validate()

    @property
    def currency(self):
        return self._currency

    @property
    def notional(self):
        return self._notional

    @property
    def start_date(self):
        return self._start_date

    @property
    def end_date(self):
        return self._end_date

    @property
    def payment_frequency(self):
        return self._payment_frequency

    @property
    def collateral_currency(self):
        return self._collateral_currency

    @property
    def daycount(self):
        return self._daycount

    @property
    def dateroll(self):
        return self._dateroll

    @property
    def pay_receive(self):
        return self._pay_receive

    @property
    def index(self):
        return self._index

    @property
    def strike(self):
        return self._strike

    @property
    def payment_lag(self):
        return self._payment_lag

    @property
    def dayroll(self):
        return self._dayroll

    def _validate(self):
        if self._start_date >= self._end_date:
            raise ValueError("Start date cannot be greater than end date")
