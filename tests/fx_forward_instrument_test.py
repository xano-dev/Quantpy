import datetime as dt
import pytest
from qp.instruments.fx.fx_forward import FXForward
from qp.utils.maps.currencies import Currency

BUY_SELL_BUY = "Buy"
BUY_SELL_SELL = "Sell"
CCY1 = Currency.EUR
CCY2 = Currency.USD
NOTIONAL1 = 1_000_000
NOTIONAL2 = 1_100_000
MATURITY_DATE = dt.date(2028, 5, 10)
COLLATERAL_CCY = Currency.EUR


@pytest.fixture
def forward_buy():
    return FXForward(
        buy_sell=BUY_SELL_BUY,
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
        collateral_ccy=COLLATERAL_CCY,
    )


@pytest.fixture
def forward_sell():
    return FXForward(
        buy_sell=BUY_SELL_SELL,
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
        collateral_ccy=COLLATERAL_CCY,
    )


# ---- Properties ----


def test_properties(forward_buy):
    assert forward_buy.buy_sell == BUY_SELL_BUY
    assert forward_buy.ccy1 == CCY1
    assert forward_buy.ccy2 == CCY2
    assert forward_buy.notional1 == NOTIONAL1
    assert forward_buy.notional2 == NOTIONAL2
    assert forward_buy.maturity_date == MATURITY_DATE
    assert forward_buy.collateral_ccy == COLLATERAL_CCY


def test_collateral_ccy_defaults_to_USD():
    forward = FXForward(
        buy_sell=BUY_SELL_BUY,
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
    )
    assert forward.collateral_ccy == Currency.USD


# ---- Strike ----


def test_strike_buy():
    # Buy: strike = notional2 / notional1
    assert FXForward(
        buy_sell="Buy",
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=1_000_000,
        notional2=1_100_000,
        maturity_date=MATURITY_DATE,
    ).strike == pytest.approx(1.1)


def test_strike_sell():
    # Sell: strike = notional1 / notional2
    assert FXForward(
        buy_sell="Sell",
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=1_100_000,
        notional2=1_000_000,
        maturity_date=MATURITY_DATE,
    ).strike == pytest.approx(1.1)


def test_strike_buy_and_sell_are_reciprocal():
    # For the same notionals, buy and sell strikes should be reciprocals of each other
    forward_buy = FXForward(
        buy_sell="Buy",
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
    )
    forward_sell = FXForward(
        buy_sell="Sell",
        ccy1=CCY1,
        ccy2=CCY2,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
    )
    assert forward_buy.strike == pytest.approx(1 / forward_sell.strike)


def run_tests():
    pytest.main([__file__, "-v"])
