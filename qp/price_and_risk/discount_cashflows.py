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
from qp.instruments.fx.fx_forward import FXForward
from qp.instruments.rates.irs import IRS
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.models.rates.irs_model import IRSModel


@dataclass
class PricingSpec:
    """Specification bundling a model, instrument, and curves required to price it.

    Args:
        model: Pricing model to apply, either `FXForwardModel` or
            `IRSModel`.
        instrument: The instrument to price, either `FXForward` or
            `IRS`.
        ir_curve: Interest rate curve used to compute discount factors,
            denominated in the collateral currency.
        fx_curves: List of FX curves, one per cashflow schedule produced by
            `model.price()`. Use `None` in each position for
            single-currency schedules and an `FXCurve` for
            cross-currency schedules. Defaults to `None`, which
            `DCFPricer` normalises to `[None] * len(schedules)`.
        value: Discounted present value of the instrument. Populated by
            :meth:`DCFPricer.discount_cashflows`; `None` until computed.

    Raises:
        ValueError: If `fx_curves` is provided but is not a list.
    """

    model: FXForwardModel | IRSModel
    instrument: FXForward | IRS
    ir_curve: IRCurve
    fx_curves: list[FXCurve | None] | None = field(default=None)
    value: float | None = field(default=None)

    def __post_init__(self):
        if self.fx_curves is not None and not isinstance(self.fx_curves, list):
            raise ValueError(
                "fx_curves must be a list of FXCurve | None, one per cashflow schedule. "
                "Use None in each position that does not require FX conversion."
            )


class DCFPricer:
    """Discounted cashflow pricer for a portfolio of pricing specifications.

    Args:
        pricing_spec: A single `PricingSpec` or a list of them.
    """

    def __init__(self, pricing_spec: PricingSpec | list[PricingSpec]):
        self._pricing_specs = (
            [pricing_spec] if isinstance(pricing_spec, PricingSpec) else pricing_spec
        )

    @property
    def pricing_specs(self):
        return self._pricing_specs

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
        collateral currency, providing an FX curve raises a warning.

        Args:
            ir_curve_currency: Currency of the IR curve.
            collateral_currency: Collateral currency of the cashflow schedule.
            currency: Cashflow currency of the schedule.
            fx_curve: FX curve for cross-currency conversion, or `None` for
                single-currency schedules.

        Raises:
            ValueError: If the IR curve currency does not match the collateral
                currency.
            ValueError: If no FX curve is provided for a cross-currency
                schedule.
            ValueError: If `fx_curve.currency_1` does not match the cashflow
                currency.
            ValueError: If `fx_curve.currency_2` does not match the
                collateral currency.

        Warns:
            UserWarning: If an FX curve is provided for a single-currency
                schedule.
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

    def discount_cashflows(self) -> list[PricingSpec]:
        """Computes the present value of each pricing spec.

        For each `PricingSpec`, calls `model.price()` to obtain
        cashflow schedules, applies discount factors from the IR curve, and
        converts to the collateral currency via the per-schedule FX curve where
        provided. The summed present value across all schedules is written to
        `spec.value`.

        Returns:
            list[PricingSpec]: The input pricing specifications with `value`
            populated.
        """
        pricing_spec_list: list[PricingSpec] = []
        for spec in self._pricing_specs:
            spec_value = 0

            cashflow_schedules = spec.model.price(spec.instrument)

            cashflow_schedules: (
                list[CashFlowSchedule] | list[PeriodicCashFlowSchedule]
            ) = (
                [cashflow_schedules]
                if (
                    isinstance(cashflow_schedules, CashFlowSchedule)
                    or isinstance(cashflow_schedules, PeriodicCashFlowSchedule)
                )
                else cashflow_schedules
            )
            ir_curve: IRCurve = spec.ir_curve

            spec.fx_curves = (
                [None] * len(cashflow_schedules)
                if spec.fx_curves is None
                else spec.fx_curves
            )

            schedule: CashFlowSchedule | PeriodicCashFlowSchedule
            fx_curve: FXCurve

            for schedule, fx_curve in zip(cashflow_schedules, spec.fx_curves):

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

                spec_value += (schedule.cashflows * discount_factors * fx_rates).sum()

            spec.value = spec_value
            pricing_spec_list.append(spec)

        return pricing_spec_list
