import numpy as np
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.curves.fx_curve import FXCurve
from qp.curves.ir_curve import IRCurve
from dataclasses import dataclass, field
from warnings import warn


@dataclass
class Instrument:
    """
    Represents a financial instrument with one or more cashflow schedules
    and the curves required to discount them.

    Attributes:
        cashflow_schedules: A single or list of cashflow schedules. A single
            schedule is automatically wrapped in a list on initialisation.
        ir_curve: The interest rate curve used to compute discount factors,
            denominated in the collateral currency.
        fx_curve: An optional FX curve for cross-currency instruments. Required
            when the cashflow currency differs from the collateral currency.
        value: The discounted present value of the instrument. Populated by
            the DCF engine; None until computed.
    """

    cashflow_schedules: CashFlowSchedule | list[CashFlowSchedule]
    ir_curve: IRCurve
    fx_curve: FXCurve | None = None
    value: float | None = field(default=None)

    def __post_init__(self):
        if isinstance(self.cashflow_schedules, CashFlowSchedule):
            self.cashflow_schedules = [self.cashflow_schedules]


class DCF:
    """
    Discounted Cashflow (DCF) engine for pricing one or more financial instruments.

    Applies discount factors from an IR curve — and optionally FX rates from an
    FX curve — to each instrument's cashflow schedules to compute present values.
    """

    def __init__(self, instruments: Instrument | list[Instrument]):
        self._instruments = (
            [instruments] if isinstance(instruments, Instrument) else instruments
        )

    @property
    def instruments(self):
        return self._instruments

    def _validate_cashflows(
        self,
        ir_curve_currency: str,
        collateral_currency: str,
        currency: str,
        fx_curve: FXCurve,
    ):
        """
        Validates that the curve and cashflow currencies are consistent.

        The IR curve must be denominated in the collateral currency. If the
        cashflow currency differs from the collateral currency, an FX curve
        must be provided. Conversely, if the cashflow currency matches the
        collateral currency, providing an FX curve is flagged as a warning.

        Args:
            ir_curve_currency: Currency of the IR curve.
            collateral_currency: Collateral currency of the cashflow schedule.
            currency: Cashflow currency of the schedule.
            fx_curve: FX curve for cross-currency conversion, or None.

        Raises:
            ValueError: If the IR curve currency does not match the collateral
                currency, or if no FX curve is provided for a cross-currency schedule.

        Warns:
            UserWarning: If an FX curve is provided for a single-currency schedule,
                as this may be unintentional.
        """

        if ir_curve_currency != collateral_currency:
            raise ValueError(
                f"IR Curve currency {ir_curve_currency} is different to collateral currency {collateral_currency} - Must provide ir_curve in collateral currency"
            )

        if currency != collateral_currency:
            # Must provide FXCurve
            if fx_curve is None:
                raise ValueError("Must provide FX curve for multi-currency deals")
        else:
            if fx_curve is not None:
                warn(
                    "FXCurve provided for a non-cross currency cashflow schedule - ensure this is intended"
                )

    def discount_cashflows(self) -> list[Instrument]:
        """
        Computes the present value of each instrument and returns them with
        their ``value`` field populated.

        For each instrument, iterates over its cashflow schedules, applies
        discount factors from the IR curve, and converts to the collateral
        currency via the FX curve if provided. The summed present value across
        all schedules is assigned to ``instrument.value``.

        Returns:
            The list of instruments with their ``value`` fields set to the
            computed present values.
        """
        instruments: list[Instrument] = []
        # For each instrument
        for instrument in self._instruments:
            instrument_value = 0
            cashflow_schedules: list[CashFlowSchedule] = instrument.cashflow_schedules
            ir_curve: IRCurve = instrument.ir_curve
            fx_curve: FXCurve = instrument.fx_curve

            for schedule in cashflow_schedules:

                self._validate_cashflows(
                    ir_curve.currency,
                    schedule.collateral_currency,
                    schedule.currency,
                    fx_curve,
                )

                discount_factors: np.ndarray = ir_curve.get_discount_factors(
                    schedule.yearfracs
                )

                fx_rates: np.ndarray = (
                    fx_curve.get_rates(schedule.yearfracs)
                    if fx_curve is not None
                    else np.ones(len(schedule.yearfracs))
                )

                discounted_cashflows: np.ndarray = (
                    schedule.cashflows * discount_factors * fx_rates
                )

                instrument_value += discounted_cashflows.sum()

            instrument.value = instrument_value
            instruments.append(instrument)

        return instruments
