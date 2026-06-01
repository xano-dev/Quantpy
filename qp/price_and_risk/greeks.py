from qp.price_and_risk.discount_cashflows import DCFPricer
from qp.price_and_risk.pricing_spec import PricingSpec


class Greeks:
    # TODO: all greeks currently read discount_cashflows()[0] — only prices the first
    # instrument in the PricingSpec. Revisit when multi-instrument specs are needed.

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

    def fx_delta(self, shock: float):
        model_fx_curves = self._pricing_spec.model.curves()["fx_curves"]

        upward_shocked_model_curves = [
            fx_curve.shock_curve(shock) for fx_curve in model_fx_curves
        ]

        downward_shocked_model_curves = [
            fx_curve.shock_curve(-shock) for fx_curve in model_fx_curves
        ]

        new_upward_curves = {
            "fx_curves": upward_shocked_model_curves,
            "ir_curves": self._pricing_spec.model.curves()["ir_curves"],
        }

        new_downward_curves = {
            "fx_curves": downward_shocked_model_curves,
            "ir_curves": self._pricing_spec.model.curves()["ir_curves"],
        }

        upward_pricing_spec = PricingSpec(
            model=self._pricing_spec.model.with_curves(new_upward_curves),
            instrument=self._pricing_spec.instrument,
            discount_curve=self._pricing_spec.discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        downward_pricing_spec = PricingSpec(
            model=self._pricing_spec.model.with_curves(new_downward_curves),
            instrument=self._pricing_spec.instrument,
            discount_curve=self._pricing_spec.discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        upward_pricer = DCFPricer(upward_pricing_spec)

        downward_pricer = DCFPricer(downward_pricing_spec)

        upward_pv = upward_pricer.discount_cashflows()[0].value
        downward_pv = downward_pricer.discount_cashflows()[0].value

        fx_delta = (upward_pv - downward_pv) / (2 * shock)

        return fx_delta

    def cross_gamma(self, fx_shock: float, ir_shock: float):

        model_curves = self._pricing_spec.model.curves()
        model_ir_curves = model_curves["ir_curves"]
        model_fx_curves = model_curves["fx_curves"]
        discount_curve = self._pricing_spec.discount_curve

        upward_shocked_model_ir = (
            None
            if model_ir_curves is None
            else [curve.shock_curve(ir_shock) for curve in model_ir_curves]
        )
        upward_shocked_discount_curve = discount_curve.shock_curve(ir_shock)

        downward_shocked_model_ir = (
            None
            if model_ir_curves is None
            else [curve.shock_curve(-ir_shock) for curve in model_ir_curves]
        )
        downward_shocked_discount_curve = discount_curve.shock_curve(-ir_shock)

        upward_shocked_model_fx = (
            None
            if model_fx_curves is None
            else [curve.shock_curve(fx_shock) for curve in model_fx_curves]
        )
        downward_shocked_model_fx = (
            None
            if model_fx_curves is None
            else [curve.shock_curve(-fx_shock) for curve in model_fx_curves]
        )

        model = self._pricing_spec.model

        pricing_spec_upfx_upir = PricingSpec(
            model=model.with_curves(
                {
                    "fx_curves": upward_shocked_model_fx,
                    "ir_curves": upward_shocked_model_ir,
                }
            ),
            instrument=self._pricing_spec.instrument,
            discount_curve=upward_shocked_discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        pricing_spec_upfx_downir = PricingSpec(
            model=model.with_curves(
                {
                    "fx_curves": upward_shocked_model_fx,
                    "ir_curves": downward_shocked_model_ir,
                }
            ),
            instrument=self._pricing_spec.instrument,
            discount_curve=downward_shocked_discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        pricing_spec_downfx_upir = PricingSpec(
            model=model.with_curves(
                {
                    "fx_curves": downward_shocked_model_fx,
                    "ir_curves": upward_shocked_model_ir,
                }
            ),
            instrument=self._pricing_spec.instrument,
            discount_curve=upward_shocked_discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        pricing_spec_downfx_downir = PricingSpec(
            model=model.with_curves(
                {
                    "fx_curves": downward_shocked_model_fx,
                    "ir_curves": downward_shocked_model_ir,
                }
            ),
            instrument=self._pricing_spec.instrument,
            discount_curve=downward_shocked_discount_curve,
            fx_curves=self._pricing_spec.fx_curves,
        )

        pv_upfx_upir = DCFPricer(pricing_spec_upfx_upir).discount_cashflows()[0].value
        pv_upfx_downir = (
            DCFPricer(pricing_spec_upfx_downir).discount_cashflows()[0].value
        )
        pv_downfx_upir = (
            DCFPricer(pricing_spec_downfx_upir).discount_cashflows()[0].value
        )
        pv_downfx_downir = (
            DCFPricer(pricing_spec_downfx_downir).discount_cashflows()[0].value
        )

        cross_gamma = (
            (pv_upfx_upir - pv_upfx_downir) - (pv_downfx_upir - pv_downfx_downir)
        ) / (4 * fx_shock * ir_shock)

        return cross_gamma
