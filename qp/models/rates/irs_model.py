from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.curves.ir_curve import IRCurve
from qp.time.cashflows.cashflow_schedule import PeriodicCashFlowSchedule
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.currency.currency_daycount import CURRENCY_DAYCOUNT
from qp.utils.maps.rates.leg_type import LegType

import numpy as np


class IRSModel:

    def __init__(
        self,
        irs: IRS,
        irs_leg_one_curve: IRCurve | None = None,
        irs_leg_two_curve: IRCurve | None = None,
    ):
        self._irs = irs
        self._irs_leg_one_curve = irs_leg_one_curve
        self._irs_leg_two_curve = irs_leg_two_curve
        self._validate()

    def _validate(self):
        for leg, curve in zip(
            self._irs.legs, [self._irs_leg_one_curve, self._irs_leg_two_curve]
        ):
            if leg.leg_type != LegType.FIXED:
                if curve is None:
                    raise ValueError("Must provide IRCurve for floating and OIS legs")

    def _compute_fixed_leg(self, leg: IRFixedLeg):

        schedule: PeriodicCashFlowSchedule = PeriodicCashFlowSchedule(
            leg.start_date,
            leg.end_date,
            leg.payment_frequency,
            leg.currency,
            leg.daycount,
            leg.dateroll,
            None,
            leg.dayroll,
            leg.collateral_currency,
        )

        cashflows = schedule.accrual_yearfracs * leg.notional * leg.fixed_rate

        schedule.set_cashflows(cashflows)

        return schedule

    def _compute_float_leg(self):
        pass

    def _compute_ois_leg(self):
        pass
