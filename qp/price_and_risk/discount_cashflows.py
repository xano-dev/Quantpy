import numpy as np
from dataclasses import dataclass, field
from warnings import warn

from qp.time.cashflows.cashflow_schedule import (
    CashFlowSchedule,
    PeriodicCashFlowSchedule,
)
from qp.time.date.daycount import yearfrac
from qp.curves.fx_curve import FXCurve
from qp.curves.ir_curve import IRCurve


@dataclass
class Instrument:
    """A financial instrument with one or more cashflow schedules and the curves
    required to discount them.

    `fx_curves` must be a list of the same length as `cashflow_schedules`,
    with `None` in each position that does not require FX conversion. Pass a
    list with an :class:`FXCurve` per foreign-currency schedule and `None` for
    any domestic schedules.

    Args:
        cashflow_schedules: A single schedule or list of schedules. A single
            schedule is automatically wrapped in a list on initialisation.
        ir_curve: Interest rate curve used to compute discount factors,
            denominated in the collateral currency.
        fx_curves: List of FX curves, one per schedule. Use `None` in each
            position for single-currency schedules and an :class:`FXCurve` for
            cross-currency schedules. Must match the length of
            `cashflow_schedules` after normalisation. Defaults to `None`,
            which is treated as `[None]` for a single-schedule instrument.
        value: Discounted present value of the instrument. Populated by
            :meth:`DCF.discount_cashflows`; `None` until computed.

    Raises:
        ValueError: If `fx_curves` is not a list.
        ValueError: If `fx_curves` length does not match `cashflow_schedules`.

    Example:
        >>> # Single-currency IRS — no FX conversion needed
        >>> Instrument(
        ...     cashflow_schedules=[fixed_schedule, float_schedule],
        ...     ir_curve=usd_curve,
        ...     fx_curves=[None, None],
        ... )

        >>> # CCIRS — EUR fixed leg converted to USD, USD float leg is domestic
        >>> Instrument(
        ...     cashflow_schedules=[eur_fixed_schedule, usd_float_schedule],
        ...     ir_curve=usd_curve,
        ...     fx_curves=[eur_usd_fx_curve, None],
        ... )

        >>> # Both legs foreign currency
        >>> Instrument(
        ...     cashflow_schedules=[eur_fixed_schedule, gbp_float_schedule],
        ...     ir_curve=usd_curve,
        ...     fx_curves=[eur_usd_fx_curve, gbp_usd_fx_curve],
        ... )
    """

    cashflow_schedules: CashFlowSchedule | list[CashFlowSchedule]
    ir_curve: IRCurve
    fx_curves: list[FXCurve | None] | None = field(default=None)
    value: float | None = field(default=None)

    def __post_init__(self):
        if isinstance(self.cashflow_schedules, CashFlowSchedule):
            self.cashflow_schedules = [self.cashflow_schedules]

        if self.fx_curves is None:
            self.fx_curves = [None] * len(self.cashflow_schedules)

        if not isinstance(self.fx_curves, list):
            raise ValueError(
                "fx_curves must be a list of FXCurve | None, one per cashflow schedule. "
                "Use None in each position that does not require FX conversion."
            )

        if len(self.fx_curves) != len(self.cashflow_schedules):
            raise ValueError(
                f"fx_curves length {len(self.fx_curves)} must match "
                f"cashflow_schedules length {len(self.cashflow_schedules)}"
            )


class DCF:
    """Discounted cashflow engine for pricing one or more financial instruments.

    Applies discount factors from an IR curve — and optionally FX rates from
    per-schedule FX curves — to each instrument's cashflow schedules to compute
    present values.

    Args:
        instruments: A single :class:`Instrument` or list of instruments to price.
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
        """Validates that the curve and cashflow currencies are consistent.

        The IR curve must be denominated in the collateral currency. If the
        cashflow currency differs from the collateral currency, an FX curve
        must be provided. Conversely, if the cashflow currency matches the
        collateral currency, providing an FX curve is flagged as a warning.

        Args:
            ir_curve_currency: Currency of the IR curve.
            collateral_currency: Collateral currency of the cashflow schedule.
            currency: Cashflow currency of the schedule.
            fx_curve: FX curve for cross-currency conversion, or `None` for
                single-currency schedules.

        Raises:
            ValueError: If the IR curve currency does not match the collateral
                currency, or if no FX curve is provided for a cross-currency
                schedule, or if the FX curve's `currency_1` does not match
                the cashflow currency, or if `currency_2` does not match the
                collateral currency.

        Warns:
            UserWarning: If an FX curve is provided for a single-currency
                schedule, as this may be unintentional.
        """

        if ir_curve_currency != collateral_currency:
            raise ValueError(
                f"IR Curve currency {ir_curve_currency} is different to collateral currency {collateral_currency} - Must provide ir_curve in collateral currency"
            )

        if currency != collateral_currency:
            if fx_curve is None:
                raise ValueError("Must provide FX curve for multi-currency deals")
            if fx_curve.currency_1 != currency:
                raise ValueError(
                    f"FX curve currency_1 {fx_curve.currency_1} does not match "
                    f"cashflow currency {currency}"
                )
            if fx_curve.currency_2 != collateral_currency:
                raise ValueError(
                    f"FX curve currency_2 {fx_curve.currency_2} does not match "
                    f"collateral currency {collateral_currency}"
                )
        else:
            if fx_curve is not None:
                warn(
                    "FXCurve provided for a non-cross currency cashflow schedule - ensure this is intended"
                )

    def discount_cashflows(self) -> list[Instrument]:
        """Computes the present value of each instrument and returns them with
        their `value` field populated.

        For each instrument, iterates over its cashflow schedules, applies
        discount factors from the IR curve, and converts to the collateral
        currency via the per-schedule FX curve if provided. The summed present
        value across all schedules is assigned to `instrument.value`.

        Returns:
            list[Instrument]: The input instruments with `value` set to the
            computed present value.
        """
        instruments: list[Instrument] = []
        for instrument in self._instruments:
            instrument_value = 0
            cashflow_schedules: (
                list[CashFlowSchedule] | list[PeriodicCashFlowSchedule]
            ) = instrument.cashflow_schedules
            ir_curve: IRCurve = instrument.ir_curve

            schedule: CashFlowSchedule | PeriodicCashFlowSchedule
            fx_curve: FXCurve

            for schedule, fx_curve in zip(cashflow_schedules, instrument.fx_curves):
                self._validate_cashflows(
                    ir_curve.currency,
                    schedule.collateral_currency,
                    schedule.currency,
                    fx_curve,
                )

                discount_factors = ir_curve.get_discount_factors(
                    yearfrac(
                        ir_curve.at_date, schedule.payment_dates, ir_curve.daycount
                    )
                )

                fx_rates = (
                    fx_curve.get_rates(
                        yearfrac(
                            fx_curve.at_date, schedule.payment_dates, fx_curve.daycount
                        )
                    )
                    if fx_curve is not None
                    else np.ones(len(schedule.payment_yearfracs))
                )

                instrument_value += (
                    schedule.cashflows * discount_factors * fx_rates
                ).sum()

            instrument.value = instrument_value
            instruments.append(instrument)

        return instruments
