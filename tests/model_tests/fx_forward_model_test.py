import datetime as dt
from unittest.mock import MagicMock, patch
import pytest

from qp.instruments.fx.fx_forward import FXForward
from qp.utils.maps.currencies import Currency
from qp.time.daycount import Daycount
from qp.models.fx.fx_forward_model import price_fx_forward

VALUATION_DATE = dt.date(2026, 5, 10)
MATURITY_DATE = dt.date(2028, 5, 10)

GET_FX_CURVE = "qp.models.fx.fx_forward_model.get_fx_curve"
FX_CURVE_CLS = "qp.models.fx.fx_forward_model.FXCurve"

DUMMY_CURVE_DATA = (MagicMock(), MagicMock(), MagicMock())


def make_forward(**kwargs):
    defaults = dict(
        buy_sell="Buy",
        base_ccy=Currency.EUR,
        term_ccy=Currency.AUD,
        notional1=1_000_000,
        notional2=500_000,
        maturity_date=MATURITY_DATE,
    )
    return FXForward(**{**defaults, **kwargs})


def fake_curve(rate):
    curve = MagicMock()
    curve.get_rates.return_value = rate
    return curve


# ---- FXForward ----


def test_strike_is_notional2_over_notional1():
    fwd = make_forward(notional1=1_000_000, notional2=1_500_000)
    assert fwd.strike == pytest.approx(1.5)


def test_default_collateral_is_usd():
    fwd = make_forward()
    assert fwd.collateral_ccy == Currency.USD


# ---- Payoff arithmetic ----


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_buy_eur_aud_payoff(mock_curve_cls, _):
    """F(AUD/EUR) = 1.127 / 0.727 ≈ 1.5502, strike = 0.5 → payoff ≈ 763,500 USD"""
    eur_curve, aud_curve = fake_curve(1.127), fake_curve(0.727)
    mock_curve_cls.side_effect = [eur_curve, aud_curve]

    _, cf = price_fx_forward(make_forward(), VALUATION_DATE)

    fwd_fx = 1.127 / 0.727
    expected = 1_000_000 * (fwd_fx - 0.5) * 0.727
    assert float(cf.amounts) == pytest.approx(expected, rel=1e-6)


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_sell_payoff_is_opposite_of_buy(mock_curve_cls, _):
    mock_curve_cls.side_effect = [fake_curve(1.127), fake_curve(0.727)]
    _, cf_buy = price_fx_forward(make_forward(buy_sell="Buy"), VALUATION_DATE)

    mock_curve_cls.side_effect = [fake_curve(1.127), fake_curve(0.727)]
    _, cf_sell = price_fx_forward(make_forward(buy_sell="Sell"), VALUATION_DATE)

    assert float(cf_buy.amounts) == pytest.approx(-float(cf_sell.amounts), rel=1e-6)


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_atm_forward_has_zero_payoff(mock_curve_cls, _):
    fwd_fx = 1.127 / 0.727
    mock_curve_cls.side_effect = [fake_curve(1.127), fake_curve(0.727)]

    atm_forward = make_forward(notional2=fwd_fx * 1_000_000)
    _, cf = price_fx_forward(atm_forward, VALUATION_DATE)

    assert float(cf.amounts) == pytest.approx(0.0, abs=1e-4)


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_payoff_doubles_with_double_notional(mock_curve_cls, _):
    mock_curve_cls.side_effect = [fake_curve(1.127), fake_curve(0.727)]
    _, cf_1x = price_fx_forward(
        make_forward(notional1=1_000_000, notional2=500_000), VALUATION_DATE
    )

    mock_curve_cls.side_effect = [fake_curve(1.127), fake_curve(0.727)]
    _, cf_2x = price_fx_forward(
        make_forward(notional1=2_000_000, notional2=1_000_000), VALUATION_DATE
    )

    assert float(cf_2x.amounts) == pytest.approx(2 * float(cf_1x.amounts), rel=1e-6)


# ---- USD leg handling ----


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_usd_base_skips_base_curve(mock_curve_cls, _):
    mock_curve_cls.return_value = fake_curve(0.727)

    price_fx_forward(
        make_forward(base_ccy=Currency.USD, term_ccy=Currency.AUD), VALUATION_DATE
    )

    assert mock_curve_cls.call_count == 1


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_usd_term_skips_term_curve(mock_curve_cls, _):
    mock_curve_cls.return_value = fake_curve(1.127)

    price_fx_forward(
        make_forward(base_ccy=Currency.EUR, term_ccy=Currency.USD), VALUATION_DATE
    )

    assert mock_curve_cls.call_count == 1


@patch(GET_FX_CURVE, return_value=DUMMY_CURVE_DATA)
@patch(FX_CURVE_CLS)
def test_eur_usd_payoff(mock_curve_cls, _):
    """EUR/USD: term curve = 1, so payoff = N1 * (F_eur - strike)."""
    mock_curve_cls.return_value = fake_curve(1.127)

    _, cf = price_fx_forward(
        make_forward(
            base_ccy=Currency.EUR,
            term_ccy=Currency.USD,
            notional1=1_000_000,
            notional2=1_100_000,
        ),
        VALUATION_DATE,
    )

    assert float(cf.amounts) == pytest.approx(1_000_000 * (1.127 - 1.10), rel=1e-6)
