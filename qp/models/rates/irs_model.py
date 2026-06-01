from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.curves.ir_curve import IRCurve
from qp.time.cashflows.cashflow_schedule import PeriodicCashFlowSchedule
from qp.time.date.daycount import yearfrac
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.leg_type import LegType
from qp.time.date.ois_fixing_dates import compute_historic_ois_fixing_dates
from qp.time.date.holiday_helper import get_holidays
from qp.models.base_model import BaseModel

import datetime as dt

import numpy as np


class IRSModel(BaseModel):
    """
    Pricing model for interest rate swaps.

    Supports fixed, floating (IBOR), and OIS legs. Computes undiscounted cashflow
    schedules for each leg of an `IRS`.

    Parameters
    ----------
    valuation_date : dt.date
        The date as of which the swap is being valued.
    leg_one_curve : IRCurve, optional
        Discount/projection curve for leg one. Required if leg one is floating or OIS.
    leg_two_curve : IRCurve, optional
        Discount/projection curve for leg two. Required if leg two is floating or OIS.
    leg_one_historic_fixings : float or list[float] or np.ndarray, optional
        Historic fixing(s) for leg one when the valuation date is past the leg start
        date. Pass a scalar float for a floating leg, or an array of daily fixings
        for an OIS leg.
    leg_two_historic_fixings : float or list[float] or np.ndarray, optional
        Historic fixing(s) for leg two. Same conventions as
        leg_one_historic_fixings.
    """

    def __init__(
        self,
        valuation_date: dt.date,
        leg_one_curve: IRCurve | None = None,
        leg_two_curve: IRCurve | None = None,
        leg_one_historic_fixings: float | list[float] | np.ndarray | None = None,
        leg_two_historic_fixings: float | list[float] | np.ndarray | None = None,
    ):
        self._valuation_date = valuation_date
        self._leg_one_curve = leg_one_curve
        self._leg_two_curve = leg_two_curve
        self._leg_one_historic_fixings = (
            leg_one_historic_fixings
            if (
                isinstance(leg_one_historic_fixings, float)
                or leg_one_historic_fixings is None
            )
            else np.array(leg_one_historic_fixings)
        )
        self._leg_two_historic_fixings = (
            leg_two_historic_fixings
            if (
                isinstance(leg_two_historic_fixings, float)
                or leg_two_historic_fixings is None
            )
            else np.array(leg_two_historic_fixings)
        )

    def _validate(self, irs: IRS):
        """
        Validates that the model has sufficient inputs to price irs.

        Parameters
        ----------
        irs : IRS
            The swap to validate against.

        Raises
        ------
        ValueError
            If a floating or OIS leg has no associated curve.
        ValueError
            If the valuation date is past a leg's start date and no historic fixings
            are provided, or if the fixings are of the wrong type for the leg type.
        """
        for leg, curve in zip(irs.legs, [self._leg_one_curve, self._leg_two_curve]):
            if leg is not None:
                if leg.leg_type != LegType.FIXED:
                    if curve is None:
                        raise ValueError(
                            "Must provide IRCurve for floating and OIS legs"
                        )

        for leg, historic_fixing in zip(
            irs.legs,
            [self._leg_one_historic_fixings, self._leg_two_historic_fixings],
        ):
            if leg is not None:

                if self._valuation_date > leg.start_date:
                    if historic_fixing is None:
                        raise ValueError(
                            "Must provide historic fixings when start date is at or before valuation date"
                        )

                    if leg.leg_type == LegType.FLOAT:
                        if not isinstance(historic_fixing, float):
                            raise ValueError(
                                "Must provide a single scalar historic fixing for a floating leg"
                            )

                    if leg.leg_type == LegType.OIS:

                        if not isinstance(historic_fixing, np.ndarray):
                            raise ValueError(
                                "Must provide a list of fixings for an OIS swap."
                            )

    def _compute_schedule(self, leg: IRFixedLeg | IRFloatingLeg):
        """
        Builds the `PeriodicCashFlowSchedule` for leg.

        Parameters
        ----------
        leg : IRFixedLeg or IRFloatingLeg
            The leg whose schedule is to be generated.

        Returns
        -------
        PeriodicCashFlowSchedule
        """
        return PeriodicCashFlowSchedule(
            leg.start_date,
            leg.end_date,
            leg.payment_frequency,
            leg.currency,
            leg.daycount,
            leg.dateroll,
            None,
            leg.dayroll,
            leg.collateral_currency,
            leg.payment_lag,
        )

    def _compute_fixed_leg(self, leg: IRFixedLeg):
        """
        Computes cashflows for a fixed leg.

        Parameters
        ----------
        leg : IRFixedLeg

        Returns
        -------
        PeriodicCashFlowSchedule
            Schedule with cashflows set to accrual_yearfrac * notional * fixed_rate,
            signed by pay/receive convention.
        """
        schedule: PeriodicCashFlowSchedule = self._compute_schedule(leg)

        cashflows = (
            schedule.accrual_yearfracs_periodic
            * leg.notional
            * leg.fixed_rate
            * (1 if leg.pay_receive == PayReceive.RECEIVE else -1)
        )

        schedule.set_cashflows(cashflows)

        return schedule

    def _compute_historic_fixing(
        self,
        leg: IRFloatingLeg,
        curve: IRCurve,
        fixings: float | np.ndarray,
        schedule: PeriodicCashFlowSchedule,
        hols: set,
    ):
        """
        Derives the effective historic fixing rate for the first period of leg.

        For a FLOAT leg, the scalar fixing is returned directly. For an OIS
        leg, daily fixings are compounded over the lookback period and annualised.

        Parameters
        ----------
        leg : IRFloatingLeg
        fixings : float or np.ndarray
            Scalar rate for FLOAT legs; array of daily overnight rates for OIS
            legs.

        Returns
        -------
        float
            Effective annualised rate for the historic period.
        """

        historic_fixing = None

        # leg is not forward starting, return historic fixing
        if leg.leg_type == LegType.FLOAT:
            historic_fixing = fixings

        elif leg.leg_type == LegType.OIS:
            daycount_denom = int(leg.daycount.split("/")[1])
            fixing_dates, future_fixing_dates = compute_historic_ois_fixing_dates(
                leg.start_date,
                self._valuation_date,
                schedule.accrual_end_dates[0],
                leg.lookback,
                leg.currency,
            )

            # validation
            if len(fixings) != (
                len(fixing_dates)
                - (len(future_fixing_dates) if len(future_fixing_dates) != 0 else 1)
            ):
                raise ValueError(
                    "Number of historic fixings must be equal to number of rate quotes between the valuation date and the start date"
                )

            if future_fixing_dates.size != 0:
                for i in range(len(future_fixing_dates) - 1):
                    d_0 = np.busday_offset(
                        future_fixing_dates[i],
                        -leg.lookback,
                        holidays=[hol.isoformat() for hol in hols],
                    )
                    d_1 = np.busday_offset(
                        future_fixing_dates[i + 1],
                        -leg.lookback,
                        holidays=[hol.isoformat() for hol in hols],
                    )
                    delta = yearfrac(d_0, d_1, leg.daycount, leg.currency)

                    d_0_df = curve.get_discount_factors(
                        yearfrac(self._valuation_date, d_0, leg.daycount, leg.currency)
                    )
                    d_1_df = curve.get_discount_factors(
                        yearfrac(self._valuation_date, d_1, leg.daycount, leg.currency)
                    )

                    future_fixing_rate = (d_0_df / d_1_df - 1) / delta

                    fixings = np.append(fixings, future_fixing_rate)

            days_diff = np.diff(fixing_dates).astype(int)
            compounded_ois_rate = (
                np.prod(1 + fixings * (days_diff / daycount_denom)) - 1
            )
            historic_fixing = compounded_ois_rate / (days_diff.sum() / daycount_denom)

        return historic_fixing

    def _compute_float_leg(
        self,
        leg: IRFloatingLeg,
        curve: IRCurve,
        fixings: float | np.ndarray,
    ):
        """
        Computes cashflows for a floating or OIS leg.

        Forward rates are implied from consecutive discount factors. If the valuation
        date is past the leg's start date, the first period rate is replaced with the
        effective historic fixing from :meth:`_compute_historic_fixing`.

        Parameters
        ----------
        leg : IRFloatingLeg
        curve : IRCurve
            Projection and discounting curve for this leg.
        fixings : float or np.ndarray
            Historic fixing(s) for the first period. See
            :meth:`_compute_historic_fixing` for conventions.

        Returns
        -------
        PeriodicCashFlowSchedule
            Schedule with cashflows signed by pay/receive convention.
        """

        schedule: PeriodicCashFlowSchedule = self._compute_schedule(leg)

        dfs = curve.get_discount_factors(
            yearfrac(curve.at_date, schedule.accrual_end_dates, curve.daycount)
        )
        dfs_offset = np.ones(dfs.size)
        dfs_offset[1:] = dfs[:-1]

        floating_rates = (dfs_offset / dfs - 1) / schedule.accrual_yearfracs_periodic

        if (
            self._valuation_date > leg.start_date
            and np.datetime64(self._valuation_date) <= schedule.accrual_end_dates[0]
        ):
            hols = get_holidays(
                leg.currency,
                (
                    leg.start_date.year - 1,
                    leg.start_date.year,
                    leg.start_date.year + 1,
                ),
            )

            floating_rates[0] = self._compute_historic_fixing(
                leg, curve, fixings, schedule, hols
            )

        cashflows = (
            schedule.accrual_yearfracs_periodic
            * leg.notional
            * (floating_rates + leg.spread)
            * (1 if leg.pay_receive == PayReceive.RECEIVE else -1)
        )

        schedule.set_cashflows(cashflows)

        return schedule

    def price(self, irs: IRS) -> list[PeriodicCashFlowSchedule]:
        """Computes undiscounted cashflow schedules for both legs of irs.

        Args:
            irs: The swap to price.

        Returns:
            list[PeriodicCashFlowSchedule]: A two-element list
            [leg_one_schedule, leg_two_schedule].

        Raises:
            ValueError: If validation fails. See :meth:`_validate`.

        Example:
            >>> fixed_leg = IRFixedLeg(
            ...     currency=Currency.USD,
            ...     notional=10_000_000,
            ...     start_date=dt.date(2024, 1, 15),
            ...     end_date=dt.date(2029, 1, 15),
            ...     payment_frequency=Frequency.SEMI_ANNUAL,
            ...     collateral_currency=Currency.USD,
            ...     daycount=Daycount.ACT_360,
            ...     dateroll=Dateroll.MODIFIED_FOLLOWING,
            ...     pay_receive=PayReceive.PAY,
            ...     fixed_rate=0.045,
            ... )
            >>> floating_leg = IRFloatingLeg(
            ...     currency=Currency.USD,
            ...     notional=10_000_000,
            ...     start_date=dt.date(2024, 1, 15),
            ...     end_date=dt.date(2029, 1, 15),
            ...     payment_frequency=Frequency.QUARTERLY,
            ...     collateral_currency=Currency.USD,
            ...     daycount=Daycount.ACT_360,
            ...     dateroll=Dateroll.MODIFIED_FOLLOWING,
            ...     pay_receive=PayReceive.RECEIVE,
            ...     index=FloatingIndex.SOFR,
            ... )
            >>> irs = IRS(fixed_leg, floating_leg)
            >>> model = IRSModel(
            ...     valuation_date=dt.date(2024, 1, 15),
            ...     leg_two_curve=sofr_curve,
            ... )
            >>> leg_one_schedule, leg_two_schedule = model.price(irs)
        """

        self._validate(irs)
        leg_schedules = []

        leg: IRFixedLeg | IRFloatingLeg

        legs = [irs.leg_one, irs.leg_two]
        curves = [self._leg_one_curve, self._leg_two_curve]
        fixings = [self._leg_one_historic_fixings, self._leg_two_historic_fixings]

        for leg, curve, fixing in zip(legs, curves, fixings):
            if leg is not None:
                if leg.leg_type == LegType.FIXED:
                    leg_schedules.append(self._compute_fixed_leg(leg))
                else:
                    leg_schedules.append(self._compute_float_leg(leg, curve, fixing))
        return leg_schedules

    def curves(self):
        return {
            "fx_curves": None,
            "ir_curves": [self._leg_one_curve, self._leg_two_curve],
        }

    def with_curves(self, curves: dict):

        return IRSModel(
            self._valuation_date,
            curves["ir_curves"][0],
            curves["ir_curves"][1],
            self._leg_one_historic_fixings,
            self._leg_two_historic_fixings,
        )
