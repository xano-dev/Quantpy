import numpy as np
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.curves.fx_curve import FXCurve
from qp.curves.ir_curve import IRCurve
from dataclasses import dataclass, field


@dataclass
class Instrument:
    cashflow_schedules: CashFlowSchedule | list[CashFlowSchedule]
    ir_curve: IRCurve
    fx_curve: FXCurve | None = None
    value: float | None = field(default=None)

    def __post_init__(self):
        if isinstance(self.cashflow_schedules, CashFlowSchedule):
            self.cashflow_schedules = [self.cashflow_schedules]


class DCF:
    """A python representation of discounted cashflows"""

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

        if ir_curve_currency != collateral_currency:
            raise ValueError(
                f"IR Curve currency {ir_curve_currency} is different to collateral currency {collateral_currency} - Must provide ir_curve in collateral currency"
            )

        if currency != collateral_currency:
            # Must provide FXCurve
            if fx_curve is None:
                raise ValueError("Must provide FX curve for multi-currency deals")

    def discount_cashflows(self) -> list[Instrument]:
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
