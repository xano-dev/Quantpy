from qp.curves.ir_curve import IRCurve
from qp.curves.fx_curve import FXCurve
from qp.instruments.fx.fx_forward import FXForward
from qp.instruments.rates.irs import IRS
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.models.rates.irs_model import IRSModel

from dataclasses import dataclass, field


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
    discount_curve: IRCurve
    fx_curves: list[FXCurve | None] | None = field(default=None)
    value: float | None = field(default=None)

    def __post_init__(self):
        if self.fx_curves is not None and not isinstance(self.fx_curves, list):
            raise ValueError(
                "fx_curves must be a list of FXCurve | None, one per cashflow schedule. "
                "Use None in each position that does not require FX conversion."
            )
