import numpy as np
from warnings import warn

from qp.time.cashflows.cashflow_schedule import (
    CashFlowSchedule,
    PeriodicCashFlowSchedule,
)
from qp.time.date.daycount import yearfrac
from qp.curves.fx_curve import FXCurve
from qp.price_and_risk.pricing_spec import PricingSpec


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

            spec.fx_curves = (
                [None] * len(cashflow_schedules)
                if spec.fx_curves is None
                else spec.fx_curves
            )

            schedule: CashFlowSchedule | PeriodicCashFlowSchedule
            fx_curve: FXCurve

            for schedule, fx_curve in zip(cashflow_schedules, spec.fx_curves):

                self._validate_cashflows(
                    spec.discount_curve.currency,
                    schedule.collateral_currency,
                    schedule.currency,
                    fx_curve,
                )

                discount_factors = spec.discount_curve.get_discount_factors(
                    yearfrac(
                        spec.discount_curve.at_date,
                        schedule.payment_dates,
                        spec.discount_curve.daycount,
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
