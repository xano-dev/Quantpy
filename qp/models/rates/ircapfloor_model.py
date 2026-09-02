import datetime as dt

import numpy as np

from qp.curves.ir_curve import IRCurve
from qp.curves.volatility.flat_vol import FlatVol
from qp.instruments.rates.ir_cap_floor import IRCapFloor
from qp.models.base_model import BaseModel
from qp.models.options.black76 import black76
from qp.models.options.intrinsic_value import compute_intrinsic_option_value
from qp.time.cashflows.cashflow_schedule import PeriodicCashFlowSchedule
from qp.time.date.daycount import yearfrac
from qp.time.date.holiday_helper import get_holidays
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.options.vol_type import VolType
from qp.utils.maps.rates.fixing_lags import FixingLags


class IRCapFloorModel(BaseModel):

    def __init__(
        self,
        valuation_date: dt.date,
        floating_curve: IRCurve,
        historic_fixings: list[float] | np.ndarray | None,
        vol_obj: FlatVol,
    ):
        self._valuation_date = valuation_date
        self._floating_curve = floating_curve
        self._historic_fixings = (
            None
            if historic_fixings is None
            else np.asarray(historic_fixings, dtype=float)
        )
        self._vol_obj = vol_obj

    def _validate(
        self,
        schedule: PeriodicCashFlowSchedule,
        fixing_dates: np.ndarray,
    ):
        valuation_date = np.datetime64(self._valuation_date)

        fixed_unsettled = (
            (fixing_dates <= valuation_date)
            & (schedule.payment_dates >= valuation_date)
        )

        if np.any(fixed_unsettled):
            if self._historic_fixings is None:
                raise ValueError(
                    "Must provide historic fixings for fixed but unsettled caplets/floorlets"
                )

            if len(self._historic_fixings) != len(fixing_dates):
                raise ValueError(
                    "Historic fixings must align with the cap/floor schedule"
                )

            if np.any(np.isnan(self._historic_fixings[fixed_unsettled])):
                raise ValueError(
                    "Historic fixing missing for fixed but unsettled caplet/floorlet"
                )

    def _compute_schedule(self, ircapfloor: IRCapFloor):

        return PeriodicCashFlowSchedule(
            ircapfloor.start_date,
            ircapfloor.end_date,
            ircapfloor.payment_frequency,
            ircapfloor.currency,
            ircapfloor.daycount,
            ircapfloor.dateroll,
            None,
            ircapfloor.dayroll,
            ircapfloor.collateral_currency,
            ircapfloor.payment_lag,
        )
    
    def _compute_fixing_dates(self, ircapfloor: IRCapFloor, schedule: PeriodicCashFlowSchedule):
        fixing_lag = FixingLags[ircapfloor.index]

        hols = get_holidays(
            ircapfloor.currency,
            years=tuple(
                np.array(schedule.accrual_start_dates, dtype="datetime64[Y]").astype(
                    int
                )
                + 1970
            ),
        )

        fixing_dates = np.busday_offset(
            [d.isoformat() for d in schedule.accrual_start_dates],
            -fixing_lag,
            holidays=[hol.isoformat() for hol in hols],
            roll="preceding",  # fixing observed day before if start date is non-business day
        )

        return fixing_dates

    def _compute_payoffs(
        self,
        ircapfloor: IRCapFloor,
        curve: IRCurve,
        schedule: PeriodicCashFlowSchedule,
        fixing_dates: np.ndarray,
    ):
        valuation_date = np.datetime64(self._valuation_date)

        fixed = fixing_dates <= valuation_date
        settled = schedule.payment_dates < valuation_date

        fixed_unsettled = fixed & ~settled
        future = ~fixed

        payoffs = np.zeros(len(fixing_dates))

        # for fixed but unsettled caplets/floorlets payoff is already known, so use intrinsic value
        if np.any(fixed_unsettled):
            payoffs[fixed_unsettled] = compute_intrinsic_option_value(
                self._historic_fixings[fixed_unsettled],
                ircapfloor.strike,
                ircapfloor.cap_floor_to_call_put(),
            )

        # for future caplets/floorlets derive forward rates and value using Black76
        if np.any(future):
            start_dfs = curve.get_discount_factors(
                yearfrac(
                    curve.at_date,
                    schedule.accrual_start_dates[future],
                    curve.daycount,
                )
            )

            end_dfs = curve.get_discount_factors(
                yearfrac(
                    curve.at_date,
                    schedule.accrual_end_dates[future],
                    curve.daycount,
                )
            )

            floating_rates = (
                (start_dfs / end_dfs - 1)
                / schedule.accrual_yearfracs_periodic[future]
            )

            expiries = yearfrac(
                self._valuation_date,
                fixing_dates[future],
                self._vol_obj.vol_dc_convention,
            )

            payoffs[future] = black76(
                floating_rates,
                ircapfloor.strike,
                expiries,
                self._vol_obj.vol,
                ircapfloor.cap_floor_to_call_put(),
                self._vol_obj.displacement
            )

        sign = (
            1
            if ircapfloor.pay_receive == PayReceive.RECEIVE
            else -1
        )

        cashflows = (
            schedule.accrual_yearfracs_periodic
            * ircapfloor.notional
            * payoffs
            * sign
        )

        schedule.set_cashflows(cashflows)

        return schedule

    def price(
        self,
        ircapfloor: IRCapFloor,
    ) -> PeriodicCashFlowSchedule:

        schedule = self._compute_schedule(ircapfloor)

        fixing_dates = self._compute_fixing_dates(
            ircapfloor,
            schedule,
        )

        self._validate(
            schedule,
            fixing_dates,
        )

        return self._compute_payoffs(
            ircapfloor,
            self._floating_curve,
            schedule,
            fixing_dates,
        )

    def curves(self):
        return {
            "fx_curves": None,
            "ir_curves": [self._floating_curve],
        }

    def with_curves(self, curves: dict):

        return IRCapFloorModel(
            self._valuation_date,
            curves["ir_curves"][0],
            self._historic_fixings,
            self._vol_obj
        )
