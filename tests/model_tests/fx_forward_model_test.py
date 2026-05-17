import datetime as dt
from unittest.mock import MagicMock
import pytest

from qp.instruments.fx.fx_forward import FXForward
from qp.models.fx.fx_forward_model import FXForwardModel
from qp.utils.maps.currencies import Currency

VALUATION_DATE = dt.date(2026, 5, 10)
MATURITY_DATE = dt.date(2028, 5, 10)


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


def make_curve(rate, currency=None, at_date=VALUATION_DATE):
    curve = MagicMock()
    curve.get_rates.return_value = rate
    curve.currency_2 = Currency.USD
    curve.at_date = at_date
    return curve


def make_model(base_rate=1.127, term_rate=0.727):
    return FXForwardModel(
        valuation_date=VALUATION_DATE,
        base_fx_curve=make_curve(base_rate),
        term_fx_curve=make_curve(term_rate),
    )


# --- FXForward ---


def test_strike_is_notional2_over_notional1():
    fwd = make_forward(notional1=1_000_000, notional2=1_500_000)
    assert fwd.strike == pytest.approx(1.5)


def test_default_collateral_is_usd():
    fwd = make_forward()
    assert fwd.collateral_ccy == Currency.USD


# --- Validation ---


def test_raises_if_base_curve_not_usd_quoted():
    base_curve = make_curve(1.127)
    base_curve.currency_2 = Currency.EUR
    with pytest.raises(ValueError):
        FXForwardModel(VALUATION_DATE, base_curve, make_curve(0.727))


def test_raises_if_term_curve_not_usd_quoted():
    term_curve = make_curve(0.727)
    term_curve.currency_2 = Currency.AUD
    with pytest.raises(ValueError):
        FXForwardModel(VALUATION_DATE, make_curve(1.127), term_curve)


def test_raises_if_base_curve_stale():
    with pytest.raises(ValueError):
        FXForwardModel(
            VALUATION_DATE,
            make_curve(1.127, at_date=dt.date(2026, 1, 1)),
            make_curve(0.727),
        )


def test_raises_if_term_curve_stale():
    with pytest.raises(ValueError):
        FXForwardModel(
            VALUATION_DATE,
            make_curve(1.127),
            make_curve(0.727, at_date=dt.date(2026, 1, 1)),
        )


# --- Payoff arithmetic ---


def test_buy_eur_aud_payoff():
    """F(AUD/EUR) = 1.127 / 0.727 ≈ 1.5502, strike = 0.5 → payoff ≈ 763,500 USD"""
    model = make_model(base_rate=1.127, term_rate=0.727)
    cf = model.price(make_forward())

    fwd_fx = 1.127 / 0.727
    expected = 1_000_000 * (fwd_fx - 0.5) * 0.727
    assert float(cf.amounts[0]) == pytest.approx(expected, rel=1e-6)


def test_sell_payoff_is_opposite_of_buy():
    cf_buy = make_model().price(make_forward(buy_sell="Buy"))
    cf_sell = make_model().price(make_forward(buy_sell="Sell"))
    assert float(cf_buy.amounts[0]) == pytest.approx(
        -float(cf_sell.amounts[0]), rel=1e-6
    )


def test_atm_forward_has_zero_payoff():
    fwd_fx = 1.127 / 0.727
    cf = make_model().price(make_forward(notional2=fwd_fx * 1_000_000))
    assert float(cf.amounts[0]) == pytest.approx(0.0, abs=1e-4)


def test_payoff_doubles_with_double_notional():
    cf_1x = make_model().price(make_forward(notional1=1_000_000, notional2=500_000))
    cf_2x = make_model().price(make_forward(notional1=2_000_000, notional2=1_000_000))
    assert float(cf_2x.amounts[0]) == pytest.approx(
        2 * float(cf_1x.amounts[0]), rel=1e-6
    )


# --- USD leg handling ---


def test_usd_base_uses_unit_rate():
    """When base is USD, F(USD/base) = 1, so fwd_fx = 1 / term_rate."""
    term_curve = make_curve(0.727)
    model = FXForwardModel(
        VALUATION_DATE,
        MagicMock(currency_2=Currency.USD, at_date=VALUATION_DATE),
        term_curve,
    )
    cf = model.price(make_forward(base_ccy=Currency.USD, term_ccy=Currency.AUD))

    fwd_fx = 1 / 0.727
    expected = 1_000_000 * (fwd_fx - 0.5) * 0.727
    assert float(cf.amounts[0]) == pytest.approx(expected, rel=1e-6)


def test_usd_term_uses_unit_rate():
    """When term is USD, F(USD/term) = 1, so fwd_fx = base_rate and payoff = N1 * (F_base - strike)."""
    cf = FXForwardModel(
        VALUATION_DATE,
        make_curve(1.127),
        MagicMock(currency_2=Currency.USD, at_date=VALUATION_DATE),
    ).price(
        make_forward(
            base_ccy=Currency.EUR,
            term_ccy=Currency.USD,
            notional1=1_000_000,
            notional2=1_100_000,
        )
    )
    assert float(cf.amounts[0]) == pytest.approx(1_000_000 * (1.127 - 1.10), rel=1e-6)


def test_eur_usd_payoff():
    """EUR/USD: term curve = 1, so payoff = N1 * (F_eur - strike)."""
    cf = FXForwardModel(
        VALUATION_DATE,
        make_curve(1.127),
        MagicMock(currency_2=Currency.USD, at_date=VALUATION_DATE),
    ).price(
        make_forward(
            base_ccy=Currency.EUR,
            term_ccy=Currency.USD,
            notional1=1_000_000,
            notional2=1_100_000,
        )
    )
    assert float(cf.amounts[0]) == pytest.approx(1_000_000 * (1.127 - 1.10), rel=1e-6)
