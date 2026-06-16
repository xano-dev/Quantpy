import datetime as dt

import numpy as np

from qp.curves.ir_curve import IRCurve
from qp.instruments.rates.ir_cap import IRCap
from qp.models.base_model import BaseModel
from qp.models.options.black76 import black76
from qp.time.cashflows.cashflow_schedule import PeriodicCashFlowSchedule
from qp.time.date.daycount import yearfrac
from qp.time.date.holiday_helper import get_holidays
from qp.utils.maps.rates.fixing_lags import FixingLags


class IRCapModel(BaseModel):

    def __init__(
        self,
        valuation_date: dt.date,
        floating_curve: IRCurve,
        historic_fixing: float | None,
        vol: float,
    ):
        self._valuation_date = valuation_date
        self._floating_curve = floating_curve
        self._historic_fixing = historic_fixing
        self._vol = vol

    def _validate(self, ircap: IRCap):
        if self._valuation_date >= ircap.start_date and self._historic_fixing is None:
            raise ValueError(
                "Must provide historic fixings when start date is at or before valuation date"
            )

    def _compute_schedule(self, ircap: IRCap):

        return PeriodicCashFlowSchedule(
            ircap.start_date,
            ircap.end_date,
            ircap.payment_frequency,
            ircap.currency,
            ircap.daycount,
            ircap.dateroll,
            None,
            ircap.dayroll,
            ircap.collateral_currency,
            ircap.payment_lag,
        )

    def _compute_payoffs(self, ircap: IRCap, curve: IRCurve, fixing: float):
        schedule = self._compute_schedule(ircap)

        dfs = curve.get_discount_factors(
            yearfrac(curve.at_date, schedule.accrual_end_dates, curve.daycount)
        )

        dfs_offset = np.ones(dfs.size)
        dfs_offset[1:] = dfs[:-1]

        if ircap.start_date > self._valuation_date:
            dfs_offset[0] = curve.get_discount_factors(
                yearfrac(curve.at_date, schedule.start_date, curve.daycount)
            )

        floating_rates = (dfs_offset / dfs - 1) / schedule.accrual_yearfracs_periodic

        if (
            self._valuation_date > ircap.start_date
            and np.datetime64(self._valuation_date) <= schedule.accrual_end_dates[0]
        ):
            floating_rates[0] = fixing

        fixing_lag = FixingLags[ircap.index]

        hols = get_holidays(
            ircap.currency,
            years=tuple(
                np.array(schedule.accrual_start_dates, dtype="datetime64[Y]").astype(
                    int
                )
                + 1970
            ),
        )

        fixing_dates = np.busday_offset(
            schedule.accrual_start_dates,
            -fixing_lag,
            holidays=[hol.isoformat() for hol in hols],
            roll="preceding",  # fixing observed day before if start date is non-business day
        )

        payoffs = black76(
            floating_rates,
            ircap.strike,
            yearfrac(
                self._valuation_date,
                fixing_dates,
                ircap.daycount,
            ),
            self._vol,
            ircap.pay_receive_to_call_put(),
        )

        cashflows = schedule.accrual_yearfracs_periodic * ircap.notional * payoffs

        schedule.set_cashflows(cashflows)

        return schedule

    def price(self, ircap: IRCap) -> PeriodicCashFlowSchedule:
        self._validate(ircap)
        return self._compute_payoffs(ircap, self._floating_curve, self._historic_fixing)

    def curves(self):
        return {
            "fx_curves": None,
            "ir_curves": [self._floating_curve],
        }

    def with_curves(self, curves: dict):

        return IRCapModel(
            self._valuation_date,
            curves["ir_curves"][0],
            self._historic_fixing,
            self._vol,
        )
