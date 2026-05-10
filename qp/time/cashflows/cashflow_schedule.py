from dateutil.relativedelta import relativedelta
import datetime as dt
from typing import Literal
import numpy as np
import pandas as pd
from calendar import monthrange

from qp.time.daycount import Daycount, yearfrac
from qp.time.dateroll import Dateroll, roll_day
from qp.utils.maps.frequencies import FREQUENCY_MAP
from qp.utils.maps.currencies import Currency


class CashFlowSchedule:
    """Python representation of a cashflow schedule. Schedule calculated exclusive of start date and inclusive of end date. Created by models/ after computing cashflow amounts.

    Args:
        start_date: start date of the schedule
        end_date: end date of the schedule
        frequency: payment frequency
        currency: currency of the schedule
        daycount: daycount convention
        dateroll: dateroll convention
        amounts: number value of each cashflow in the schedule
        dayroll: roll day of the schedule
    Example:
        >>> cf_schedule = CashFlowSchedule(
        ...     start_date=dt.date(2026, 1, 1),
        ...     end_date=dt.date(2026, 12, 31),
        ...     frequency="quarterly",
        ...     currency=Currency.USD,
        ...     daycount=Daycount.ACT_360,
        ...     dateroll=Dateroll.MODIFIED_FOLLOWING,
        ...     amounts=np.array([10, 20, 30, 40]),
        ...     dayroll=16
        ... )
    Raises:
        ValueError: if dayroll exceeds 31.
        ValueError: if amounts length does not match number of payment dates.
    """

    def __init__(
        self,
        start_date: dt.date,
        end_date: dt.date,
        frequency: Literal["monthly", "quarterly", "semiannual", "annual"],
        currency: Currency,
        daycount: Daycount,
        dateroll: Dateroll,
        amounts: np.ndarray,
        dayroll: int | None = None,
    ):
        self._start_date = start_date
        self._end_date = end_date
        self._frequency = frequency
        self._currency = currency
        self._daycount = daycount
        self._dateroll = dateroll
        self._amounts = amounts

        if dayroll is None:
            self._dayroll = end_date.day
        else:
            self._dayroll = dayroll

        if self._dayroll > 31:
            raise ValueError(f"Invalid dayroll: {self._dayroll}")

        self._payment_dates = self._generate_dates()

        if len(self._amounts) != len(self._payment_dates):
            raise ValueError(
                f"amounts length {len(self._amounts)} does not match "
                f"number of payment dates {len(self._payment_dates)}"
            )

        self._yearfracs: np.ndarray = self._generate_yearfracs()

    @property
    def start_date(self):
        return self._start_date

    @property
    def end_date(self):
        return self._end_date

    @property
    def frequency(self):
        return self._frequency

    @property
    def currency(self):
        return self._currency

    @property
    def daycount(self):
        return self._daycount

    @property
    def dateroll(self):
        return self._dateroll

    @property
    def amounts(self):
        return self._amounts

    @property
    def payment_dates(self):
        return self._payment_dates

    @property
    def yearfracs(self):
        return self._yearfracs

    @property
    def dayroll(self):
        return self._dayroll

    def _apply_dayroll(self, year: int, month: int):
        max_day = monthrange(year, month)[1]
        day = min(self._dayroll, max_day)
        return dt.date(year, month, day)

    def _generate_dates(self):

        step: relativedelta = FREQUENCY_MAP[self._frequency]

        stepped = self._end_date - step
        step_date = self._apply_dayroll(stepped.year, stepped.month)

        payment_dates: list = [self._end_date]

        while step_date > self._start_date:
            rolled_date = roll_day(step_date, self._dateroll, self._currency)
            payment_dates.append(rolled_date)
            stepped = step_date - step
            step_date = self._apply_dayroll(stepped.year, stepped.month)

        return np.sort(np.array(payment_dates))

    def _generate_yearfracs(self):
        yearfracs: list = []
        for date in self._payment_dates:
            yf: float = yearfrac(self._start_date, date, self._daycount, self._currency)
            yearfracs.append(yf)
        return np.array(yearfracs)

    def to_dataframe(self):
        return pd.DataFrame(
            {
                "Payment Date": self._payment_dates,
                "DCF": self._yearfracs,
                "Cashflow": self._amounts,
            }
        )

    def _repr_html_(self):
        return self.to_dataframe()._repr_html_()
