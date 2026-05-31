from qp.price_and_risk.discount_cashflows import DCFPricer
from qp.price_and_risk.pricing_spec import PricingSpec


class Greeks:

    def __init__(self, pricing_spec: PricingSpec, pricer: DCFPricer):
        self._pricing_spec = pricing_spec
        self._pricer = pricer

    def parallel_dv01(self, shock: float):

        model_curves = self._pricing_spec.model.curves()
        ir_curves = model_curves["ir_curves"]

        discount_curve = self._pricing_spec.discount_curve

        upward_shocked_model_curves = (
            [
                curve.shock_curve(shock) if curve is not None else None
                for curve in ir_curves
            ]
            if ir_curves is not None
            else ir_curves
        )

        upward_shocked_discount_curve = discount_curve.shock_curve(shock)

        new_upward_curves = {
            "fx_curves": model_curves["fx_curves"],
            "ir_curves": upward_shocked_model_curves,
        }

        downward_shocked_model_curves = (
            [
                curve.shock_curve(-shock) if curve is not None else None
                for curve in ir_curves
            ]
            if ir_curves is not None
            else ir_curves
        )
        downward_shocked_discount_curve = discount_curve.shock_curve(-shock)

        new_downward_curves = {
            "fx_curves": model_curves["fx_curves"],
            "ir_curves": downward_shocked_model_curves,
        }

        upward_pricing_spec = PricingSpec(
            model=self._pricing_spec.model.with_curves(new_upward_curves),
            discount_curve=upward_shocked_discount_curve,
            instrument=self._pricing_spec.instrument,
            fx_curves=self._pricing_spec.fx_curves,
        )

        upward_pricer = DCFPricer(upward_pricing_spec)

        downward_pricing_spec = PricingSpec(
            model=self._pricing_spec.model.with_curves(new_downward_curves),
            discount_curve=downward_shocked_discount_curve,
            instrument=self._pricing_spec.instrument,
            fx_curves=self._pricing_spec.fx_curves,
        )

        downward_pricer = DCFPricer(downward_pricing_spec)

        upward_pv = upward_pricer.discount_cashflows()[0].value
        downward_pv = downward_pricer.discount_cashflows()[0].value

        dv01 = 0.0001 * (upward_pv - downward_pv) / (2 * shock)

        return dv01
