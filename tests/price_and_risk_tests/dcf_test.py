import datetime as dt
from unittest.mock import MagicMock
import numpy as np
import pytest

from qp.price_and_risk.discount_cashflows import DCF, Instrument
from qp.time.cashflows.cashflow_schedule import CashFlowSchedule
from qp.curves.ir_curve import IRCurve
from qp.instruments.rates.irs import IRS, IRFixedLeg, IRFloatingLeg
from qp.models.rates.irs_model import IRSModel
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex
from qp.time.date.daycount import Daycount
from qp.time.date.dateroll import Dateroll

VALUATION_DATE = dt.date(2026, 6, 1)
START_DATE = dt.date(2026, 6, 3)
END_DATE = dt.date(2028, 6, 3)
NOTIONAL = 10_000_000


# --- Helpers ---


def make_ir_curve_mock(currency: Currency, discount_factors):
    curve = MagicMock()
    curve.currency = currency
    curve.get_discount_factors.return_value = np.array(discount_factors, dtype=float)
    curve.at_date = VALUATION_DATE
    curve.daycount = Daycount.ACT_360
    return curve


def make_fx_curve_mock(fx_rates, currency_1=Currency.EUR, currency_2=Currency.USD):
    curve = MagicMock()
    curve.get_rates.return_value = np.array(fx_rates, dtype=float)
    curve.at_date = VALUATION_DATE
    curve.daycount = Daycount.ACT_360
    curve.currency_1 = currency_1
    curve.currency_2 = currency_2
    return curve


def make_schedule(cashflows, currency=Currency.USD, collateral_currency=Currency.USD):
    n = len(cashflows)
    start = dt.date(2026, 1, 1)
    payment_dates = [dt.date(2026 + i, 1, 2) for i in range(1, n + 1)]
    return CashFlowSchedule(
        start_date=start,
        payment_dates=payment_dates,
        cashflows=np.array(cashflows, dtype=float),
        currency=currency,
        daycount=Daycount.ACT_360,
        collateral_currency=collateral_currency,
    )


def make_instrument(
    cashflows,
    discount_factors,
    currency=Currency.USD,
    collateral_currency=Currency.USD,
    fx_curves=None,
):
    return Instrument(
        cashflow_schedules=make_schedule(cashflows, currency, collateral_currency),
        ir_curve=make_ir_curve_mock(collateral_currency, discount_factors),
        fx_curves=fx_curves,
    )


def make_usd_ir_curve(tenors, discount_factors):
    return IRCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_360,
        currency=Currency.USD,
        curve_name="USD_SOFR",
        tenors=tenors,
        discount_factors=discount_factors,
    )


def make_ccirs(
    pay_currency: Currency,
    receive_currency: Currency,
    fixed_rate: float = 0.05,
    notional: float = 1_000_000,
    start: dt.date = dt.date(2026, 6, 3),
    end: dt.date = dt.date(2026, 12, 3),
) -> IRS:
    return IRS(
        leg_one=IRFixedLeg(
            currency=pay_currency,
            notional=notional,
            start_date=start,
            end_date=end,
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.THIRTY_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.PAY,
            fixed_rate=fixed_rate,
        ),
        leg_two=IRFloatingLeg(
            currency=receive_currency,
            notional=notional,
            start_date=start,
            end_date=end,
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.ACT_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.RECEIVE,
            index=FloatingIndex.SOFR,
        ),
    )


# --- Instrument dataclass ---


def test_instrument_wraps_single_schedule_in_list():
    schedule = make_schedule([1_000.0])
    instrument = Instrument(
        cashflow_schedules=schedule,
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
    )
    assert isinstance(instrument.cashflow_schedules, list)
    assert len(instrument.cashflow_schedules) == 1


def test_instrument_preserves_list_of_schedules():
    schedules = [make_schedule([1_000.0]), make_schedule([2_000.0])]
    instrument = Instrument(
        cashflow_schedules=schedules,
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
    )
    assert len(instrument.cashflow_schedules) == 2


# --- Validation ---


def test_raises_if_fx_curve_currency_1_does_not_match_cashflow_currency():
    instrument = Instrument(
        cashflow_schedules=make_schedule(
            [1_000.0], currency=Currency.EUR, collateral_currency=Currency.USD
        ),
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
        fx_curves=[
            make_fx_curve_mock([1.10], currency_1=Currency.GBP, currency_2=Currency.USD)
        ],
    )
    with pytest.raises(ValueError, match="currency_1"):
        DCF(instrument).discount_cashflows()


def test_raises_if_fx_curve_currency_2_does_not_match_collateral_currency():
    instrument = Instrument(
        cashflow_schedules=make_schedule(
            [1_000.0], currency=Currency.EUR, collateral_currency=Currency.USD
        ),
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
        fx_curves=[
            make_fx_curve_mock([1.10], currency_1=Currency.EUR, currency_2=Currency.GBP)
        ],
    )
    with pytest.raises(ValueError, match="currency_2"):
        DCF(instrument).discount_cashflows()


def test_raises_if_fx_curves_is_not_a_list():
    with pytest.raises(ValueError, match="fx_curves must be a list"):
        Instrument(
            cashflow_schedules=make_schedule([1_000.0]),
            ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
            fx_curves=make_fx_curve_mock([1.10]),  # bare curve, not a list
        )


def test_raises_if_ir_curve_currency_does_not_match_collateral():
    instrument = Instrument(
        cashflow_schedules=make_schedule([1_000.0], collateral_currency=Currency.USD),
        ir_curve=make_ir_curve_mock(Currency.EUR, [0.95]),
    )
    with pytest.raises(ValueError):
        DCF(instrument).discount_cashflows()


def test_raises_if_cross_currency_schedule_has_no_fx_curve():
    instrument = Instrument(
        cashflow_schedules=make_schedule(
            [1_000.0], currency=Currency.EUR, collateral_currency=Currency.USD
        ),
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
        fx_curves=None,
    )
    with pytest.raises(ValueError):
        DCF(instrument).discount_cashflows()


def test_warns_if_fx_curve_provided_for_single_currency_schedule():
    instrument = Instrument(
        cashflow_schedules=make_schedule(
            [1_000.0], currency=Currency.USD, collateral_currency=Currency.USD
        ),
        ir_curve=make_ir_curve_mock(Currency.USD, [0.95]),
        fx_curves=[make_fx_curve_mock([1.0])],
    )
    with pytest.warns(UserWarning):
        DCF(instrument).discount_cashflows()


# --- Single-currency discounting ---


def test_single_cashflow_discounted():
    result = DCF(make_instrument([1_000.0], [0.95])).discount_cashflows()
    expected = 1000 * 0.95
    assert result[0].value == pytest.approx(expected, rel=1e-6)


def test_multiple_cashflows_summed():
    result = DCF(make_instrument([1_000.0, 2_000.0], [0.95, 0.90])).discount_cashflows()
    expected = 1000 * 0.95 + 2000 * 0.9
    assert result[0].value == pytest.approx(expected, rel=1e-6)


def test_discount_factors_of_one_give_undiscounted_sum():
    cashflows = [1_000.0, 2_000.0, 3_000.0]
    result = DCF(make_instrument(cashflows, [1.0, 1.0, 1.0])).discount_cashflows()
    assert result[0].value == pytest.approx(sum(cashflows), rel=1e-6)


def test_zero_cashflows_give_zero_pv():
    result = DCF(make_instrument([0.0, 0.0], [0.95, 0.90])).discount_cashflows()
    assert result[0].value == pytest.approx(0.0, abs=1e-10)


def test_negative_cashflows_give_negative_pv():
    result = DCF(
        make_instrument([-1_000.0, -2_000.0], [0.95, 0.90])
    ).discount_cashflows()
    assert result[0].value < 0


# --- Cross-currency discounting ---


def test_cross_currency_pv_applies_fx_rates():
    result = DCF(
        make_instrument(
            [1_000.0],
            [0.95],
            currency=Currency.EUR,
            collateral_currency=Currency.USD,
            fx_curves=[make_fx_curve_mock([1.10])],
        )
    ).discount_cashflows()
    expected = 1000 * 0.95 * 1.1
    assert result[0].value == pytest.approx(expected, rel=1e-6)


def test_unit_fx_rates_match_single_currency_pv():
    """FX of 1 on a cross-ccy schedule must yield the same PV as the same-ccy case."""
    pv_single = DCF(make_instrument([1_000.0], [0.95])).discount_cashflows()[0].value
    pv_cross = (
        DCF(
            make_instrument(
                [1_000.0],
                [0.95],
                currency=Currency.EUR,
                collateral_currency=Currency.USD,
                fx_curves=[make_fx_curve_mock([1.0])],
            )
        )
        .discount_cashflows()[0]
        .value
    )
    assert pv_single == pytest.approx(pv_cross, rel=1e-6)


# --- Multi-schedule instrument ---


def test_two_schedules_on_one_instrument_pv_is_sum():
    ir_curve = make_ir_curve_mock(Currency.USD, [0.95])
    instrument = Instrument(
        cashflow_schedules=[make_schedule([1_000.0]), make_schedule([2_000.0])],
        ir_curve=ir_curve,
    )
    result = DCF(instrument).discount_cashflows()
    expected = 1000 * 0.95 + 2000 * 0.95
    assert result[0].value == pytest.approx(expected, rel=1e-6)


# --- Multi-instrument ---


def test_two_instruments_both_get_values():
    results = DCF(
        [make_instrument([1_000.0], [0.95]), make_instrument([2_000.0], [0.90])]
    ).discount_cashflows()
    assert len(results) == 2
    assert results[0].value is not None
    assert results[1].value is not None


def test_instrument_values_are_independent():
    """Each instrument is valued separately using its own curve."""
    results = DCF(
        [make_instrument([1_000.0], [0.95]), make_instrument([2_000.0], [0.90])]
    ).discount_cashflows()
    expected_0 = 1000 * 0.95
    expected_1 = 2000 * 0.90
    assert results[0].value == pytest.approx(expected_0, rel=1e-6)
    assert results[1].value == pytest.approx(expected_1, rel=1e-6)


# --- IRS end-to-end ---


def test_irs_dcf_pv_hand_computed():
    """
    End-to-end: IRSModel → CashFlowSchedule → DCF → PV, verified by hand.

    Setup
    -----
    Both legs quarterly, 2 periods (6-month swap). Using a mock curve that
    returns DFs = [0.99, 0.97] for every lookup, so the arithmetic is exact.

    Hand calculation
    ----------------
    Float leg (RECEIVE, ACT/360):
        The float cashflow formula is N * (DF_prev / DF_curr - 1), and tau cancels.
        CF_1 = N * (1 / 0.99 - 1),   DF_0 = 1 (start of swap)
        CF_2 = N * (0.99 / 0.97 - 1)

        Float PV = CF_1 * 0.99 + CF_2 * 0.97
        Cross-check with the telescoping identity: Float PV = N * (1 - 0.97)

    Fixed leg (PAY, 30/360, FIXED_RATE, quarterly tau = 90/360 = 0.25):
        CF_1 = -N * FIXED_RATE * 0.25
        CF_2 = -N * FIXED_RATE * 0.25

        Fixed PV = CF_1 * 0.99 + CF_2 * 0.97

    Expected net PV = Float PV + Fixed PV
    """
    FIXED_RATE = 0.05
    N = 1_000_000
    START = dt.date(2026, 6, 3)
    END = dt.date(2026, 12, 3)

    mock_curve = make_ir_curve_mock(Currency.USD, [0.99, 0.97])

    irs = IRS(
        leg_one=IRFixedLeg(
            currency=Currency.USD,
            notional=N,
            start_date=START,
            end_date=END,
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.THIRTY_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.PAY,
            fixed_rate=FIXED_RATE,
        ),
        leg_two=IRFloatingLeg(
            currency=Currency.USD,
            notional=N,
            start_date=START,
            end_date=END,
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.ACT_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.RECEIVE,
            index=FloatingIndex.SOFR,
        ),
    )

    schedules = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=mock_curve).price(
        irs
    )
    instrument = Instrument(cashflow_schedules=list(schedules), ir_curve=mock_curve)
    result = DCF(instrument).discount_cashflows()

    expected_fixed = N * FIXED_RATE * 0.25 * 0.99 + N * FIXED_RATE * 0.25 * 0.97
    expected_float = N * (1 / 0.99 - 1) * 0.99 + N * (0.99 / 0.97 - 1) * 0.97
    expected = expected_float - expected_fixed
    assert result[0].value == pytest.approx(expected, rel=1e-4)


# --- CCIRS end-to-end ---


def test_ccirs_dcf_pv_hand_computed():
    """
    End-to-end: pay EUR fixed, receive USD floating, collateral USD.

    Hand calculation
    ----------------
    USD curve DFs:  [0.99, 0.97]  (used for both discounting and float projection)
    EUR/USD FX:     1.10 flat     (EUR cashflows converted to USD)

    Float leg (RECEIVE USD, same as single-ccy IRS test):
        Float PV = N * (1 - 0.97)   [telescoping identity]
                 = 1_000_000 * 0.03 = 30_000 USD

    Fixed leg (PAY EUR, 30/360 tau = 0.25):
        CF_1 = -N * 0.05 * 0.25 = -12_500 EUR  → -13_750 USD at 1.10
        CF_2 = -N * 0.05 * 0.25 = -12_500 EUR  → -13_750 USD at 1.10

        Fixed PV = -13_750 * 0.99 + -13_750 * 0.97

    Expected net PV = Float PV + Fixed PV
    """
    N = 1_000_000
    FIXED_RATE = 0.05
    SPOT = 1.10

    usd_curve = make_ir_curve_mock(Currency.USD, [0.99, 0.97])
    fx_curve = make_fx_curve_mock([SPOT, SPOT])

    irs = make_ccirs(
        pay_currency=Currency.EUR,
        receive_currency=Currency.USD,
        fixed_rate=FIXED_RATE,
        notional=N,
    )

    schedules = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=usd_curve, leg_two_curve=usd_curve
    ).price(irs)

    # One instrument: EUR fixed leg gets FX curve, USD float leg gets None
    instrument = Instrument(
        cashflow_schedules=list(schedules),
        ir_curve=usd_curve,
        fx_curves=[fx_curve, None],
    )
    results = DCF(instrument).discount_cashflows()

    expected_float = N * (1 / 0.99 - 1) * 0.99 + N * (0.99 / 0.97 - 1) * 0.97
    expected_fixed = (
        -N * FIXED_RATE * 0.25 * SPOT * 0.99 + -N * FIXED_RATE * 0.25 * SPOT * 0.97
    )
    expected_net = expected_float + expected_fixed
    assert results[0].value == pytest.approx(expected_net, rel=1e-4)


def test_ccirs_higher_fx_rate_increases_eur_fixed_leg_pv():
    """A higher EUR/USD spot rate increases the USD-equivalent PV of EUR cashflows."""
    usd_curve = make_ir_curve_mock(Currency.USD, [0.99, 0.97])

    irs = make_ccirs(pay_currency=Currency.EUR, receive_currency=Currency.USD)
    schedules = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=usd_curve, leg_two_curve=usd_curve
    ).price(irs)

    def pv_fixed_leg(spot):
        instrument = Instrument(
            cashflow_schedules=schedules[0],
            ir_curve=usd_curve,
            fx_curves=[make_fx_curve_mock([spot, spot])],
        )
        return DCF(instrument).discount_cashflows()[0].value

    # fixed leg is PAY so cashflows are negative — higher FX makes PV more negative
    assert pv_fixed_leg(1.20) < pv_fixed_leg(1.05)


def test_ccirs_unit_fx_matches_single_currency_fixed_leg_pv():
    """With FX = 1.0, a EUR fixed leg must produce the same PV as an equivalent USD fixed leg."""
    usd_curve = make_ir_curve_mock(Currency.USD, [0.99, 0.97])

    irs_eur = make_ccirs(pay_currency=Currency.EUR, receive_currency=Currency.USD)
    irs_usd = make_ccirs(pay_currency=Currency.USD, receive_currency=Currency.USD)

    schedules_eur = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=usd_curve, leg_two_curve=usd_curve
    ).price(irs_eur)
    schedules_usd = IRSModel(
        valuation_date=VALUATION_DATE, leg_one_curve=usd_curve, leg_two_curve=usd_curve
    ).price(irs_usd)

    pv_eur = (
        DCF(
            Instrument(
                schedules_eur[0], usd_curve, fx_curves=[make_fx_curve_mock([1.0, 1.0])]
            )
        )
        .discount_cashflows()[0]
        .value
    )

    pv_usd = DCF(Instrument(schedules_usd[0], usd_curve)).discount_cashflows()[0].value

    assert pv_eur == pytest.approx(pv_usd, rel=1e-6)


def test_ccirs_both_legs_foreign_currency():
    """Both legs in non-USD currencies, both with FX curves, collateral USD."""
    N = 1_000_000
    usd_curve = make_ir_curve_mock(Currency.USD, [0.99, 0.97])
    eur_fx = make_fx_curve_mock(
        [1.10, 1.10], currency_1=Currency.EUR, currency_2=Currency.USD
    )
    gbp_fx = make_fx_curve_mock(
        [1.25, 1.25], currency_1=Currency.GBP, currency_2=Currency.USD
    )

    irs = IRS(
        leg_one=IRFixedLeg(
            currency=Currency.EUR,
            notional=N,
            start_date=dt.date(2026, 6, 3),
            end_date=dt.date(2026, 12, 3),
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.THIRTY_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.PAY,
            fixed_rate=0.05,
        ),
        leg_two=IRFloatingLeg(
            currency=Currency.GBP,
            notional=N,
            start_date=dt.date(2026, 6, 3),
            end_date=dt.date(2026, 12, 3),
            payment_frequency=Frequency.QUARTERLY,
            collateral_currency=Currency.USD,
            daycount=Daycount.ACT_360,
            dateroll=Dateroll.MODIFIED_FOLLOWING,
            pay_receive=PayReceive.RECEIVE,
            index=FloatingIndex.SONIA,
        ),
    )

    schedules = IRSModel(valuation_date=VALUATION_DATE, leg_two_curve=usd_curve).price(
        irs
    )

    # One instrument: per-schedule FX curves for EUR and GBP legs
    result = DCF(
        Instrument(
            cashflow_schedules=list(schedules),
            ir_curve=usd_curve,
            fx_curves=[eur_fx, gbp_fx],
        )
    ).discount_cashflows()

    assert result[0].value is not None
    assert result[0].value != pytest.approx(0.0, abs=1.0)
