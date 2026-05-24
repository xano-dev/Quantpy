import datetime as dt
from typing import Literal

from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.leg_type import LegType
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll


class IRBaseLeg:
    """Base class for interest rate swap legs.

    Contains the common attributes shared by all leg types.

    Args:
        currency: Currency of the cashflows.
        notional: Notional amount of the leg.
        start_date: Accrual start date of the leg.
        end_date: Accrual end date of the leg.
        payment_frequency: Frequency of coupon payments.
        collateral_currency: Discount currency for present value calculations.
        daycount: Daycount convention for accrual calculations.
        dateroll: Business-day adjustment convention.
        pay_receive: Whether the leg is paid or received.
        payment_lag: Number of business days between accrual end and payment date.
        dayroll: Roll day of the contract - defaults to the end date's day
    """

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
        pay_receive: PayReceive,
        payment_lag: int = 0,
        dayroll: int = None,
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
        self._payment_lag = payment_lag
        self._dayroll = dayroll if dayroll is not None else end_date.day

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
    def payment_lag(self):
        return self._payment_lag

    @property
    def dayroll(self):
        return self._dayroll


class IRFixedLeg(IRBaseLeg):
    """Fixed leg of an interest rate swap.

    Pays a fixed coupon at each payment date, computed from `fixed_rate`
    applied to the notional over each accrual period. Extends `IRBaseLeg`.

    Args:
        fixed_rate: Fixed coupon rate as a decimal (e.g. `0.05` for 5%).
    """

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
        pay_receive: PayReceive,
        fixed_rate: float,
        payment_lag: int = 0,
        dayroll: int = None,
    ):
        super().__init__(
            currency,
            notional,
            start_date,
            end_date,
            payment_frequency,
            collateral_currency,
            daycount,
            dateroll,
            pay_receive,
            payment_lag,
            dayroll,
        )
        self._fixed_rate = fixed_rate
        self._leg_type = LegType.FIXED

    @property
    def fixed_rate(self):
        return self._fixed_rate

    @property
    def leg_type(self):
        return self._leg_type


class IRFloatingLeg(IRBaseLeg):
    """Floating leg of an interest rate swap.

    Pays a floating coupon at each payment date, referencing `index`
    plus an optional `spread`. Extends `IRBaseLeg`.

    Args:
        index: Floating rate index (e.g. `FloatingIndex.SOFR`).
        spread: Spread over the index as a decimal. Defaults to `0.0`.
        lookback: Lookback for OIS (Overnight Index Swaps) - defaults to 30
    """

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
        pay_receive: PayReceive,
        index: FloatingIndex,
        spread: float = 0.0,
        payment_lag: int = 0,
        dayroll: int = None,
        leg_type: Literal[LegType.FLOAT, LegType.OIS] = LegType.FLOAT,
        lookback: int = 30,
    ):
        super().__init__(
            currency,
            notional,
            start_date,
            end_date,
            payment_frequency,
            collateral_currency,
            daycount,
            dateroll,
            pay_receive,
            payment_lag,
            dayroll,
        )
        self._index = index
        self._spread = spread
        self._leg_type = leg_type
        self._lookback = lookback

    @property
    def index(self):
        return self._index

    @property
    def spread(self):
        return self._spread

    @property
    def lookback(self):
        return self._lookback

    @property
    def leg_type(self):
        return self._leg_type


class IRS:

    def __init__(
        self, leg_one: IRFixedLeg | IRFloatingLeg, leg_two: IRFixedLeg | IRFloatingLeg
    ):
        self.__leg_one = leg_one
        self.__leg_two = leg_two
        pass

    @property
    def leg_one(self):
        return self.__leg_one

    @property
    def leg_two(self):
        return self.__leg_two

    @property
    def legs(self):
        return [self.__leg_one, self.__leg_two]
