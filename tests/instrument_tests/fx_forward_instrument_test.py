import datetime as dt
import pytest
from qp.instruments.fx.fx_forward import FXForward
from qp.utils.maps.currencies import Currency
from qp.utils.maps.buysell import BuySell

BUY_SELL_BUY = BuySell.BUY
BUY_SELL_SELL = BuySell.SELL
BASE_CCY = Currency.EUR
TERM_CCY = Currency.USD
NOTIONAL1 = 1_000_000
NOTIONAL2 = 1_100_000
MATURITY_DATE = dt.date(2028, 5, 10)
COLLATERAL_CCY = Currency.EUR


@pytest.fixture
def forward_buy():
    return FXForward(
        buy_sell=BUY_SELL_BUY,
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
        collateral_ccy=COLLATERAL_CCY,
    )


@pytest.fixture
def forward_sell():
    return FXForward(
        buy_sell=BUY_SELL_SELL,
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
        collateral_ccy=COLLATERAL_CCY,
    )


# ---- Properties ----


def test_properties(forward_buy):
    assert forward_buy.buy_sell == BUY_SELL_BUY
    assert forward_buy.base_ccy == BASE_CCY
    assert forward_buy.term_ccy == TERM_CCY
    assert forward_buy.notional1 == NOTIONAL1
    assert forward_buy.notional2 == NOTIONAL2
    assert forward_buy.maturity_date == MATURITY_DATE
    assert forward_buy.collateral_ccy == COLLATERAL_CCY


def test_collateral_ccy_defaults_to_USD():
    forward = FXForward(
        buy_sell=BUY_SELL_BUY,
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
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
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=1_000_000,
        notional2=1_100_000,
        maturity_date=MATURITY_DATE,
    ).strike == pytest.approx(1.1)


def test_strike_sell():
    # Sell: strike = notional2 / notional1
    assert FXForward(
        buy_sell="Sell",
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=1_100_000,
        notional2=1_000_000,
        maturity_date=MATURITY_DATE,
    ).strike == pytest.approx(0.90909090909)


def test_strike_buy_and_sell_are_equal():
    # For the same notionals, buy and sell strikes should be the same
    forward_buy = FXForward(
        buy_sell="Buy",
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
    )
    forward_sell = FXForward(
        buy_sell="Sell",
        base_ccy=BASE_CCY,
        term_ccy=TERM_CCY,
        notional1=NOTIONAL1,
        notional2=NOTIONAL2,
        maturity_date=MATURITY_DATE,
    )
    assert forward_buy.strike == forward_sell.strike


def run_tests():
    pytest.main([__file__, "-v"])
