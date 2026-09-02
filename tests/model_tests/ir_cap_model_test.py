import datetime as dt

import numpy as np
import pytest

from qp.curves.ir_curve import IRCurve
from qp.instruments.rates.ir_cap_floor import IRCapFloor
from qp.models.rates.ircapfloor_model import IRCapFloorModel
from qp.time.date.dateroll import Dateroll
from qp.time.date.daycount import Daycount
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.rates.floating_indexes import FloatingIndex

VALUATION_DATE = dt.date(2026, 6, 1)
START_DATE = dt.date(2026, 6, 3)  # spot-starting T+2
END_DATE_2Y = dt.date(2028, 6, 3)
NOTIONAL = 10_000_000
STRIKE = 0.05
VOL = 0.20


def make_ir_cap(**kwargs):
    defaults = dict(
        currency=Currency.USD,
        notional=NOTIONAL,
        start_date=START_DATE,
        end_date=END_DATE_2Y,
        payment_frequency=Frequency.QUARTERLY,
        collateral_currency=Currency.USD,
        daycount=Daycount.ACT_360,
        dateroll=Dateroll.MODIFIED_FOLLOWING,
        pay_receive=PayReceive.RECEIVE,  # long cap
        index=FloatingIndex.TERM_SOFR_3M,
        strike=STRIKE,
    )
    return IRCapFloor(**{**defaults, **kwargs})


def make_ir_curve(discount_factors):
    dfs = np.array(discount_factors)
    n = len(dfs)
    tenors = np.array([i * 0.25 for i in range(1, n + 1)])
    return IRCurve(
        at_date=VALUATION_DATE,
        daycount=Daycount.ACT_360,
        currency=Currency.USD,
        curve_name="USD_TEST",
        tenors=tenors,
        discount_factors=dfs,
        extrapolate=True,
    )


def make_model(curve=None, historic_fixing=None, vol=VOL, **kwargs):
    if curve is None:
        curve = make_ir_curve([0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92])
    defaults = dict(
        valuation_date=VALUATION_DATE,
        floating_curve=curve,
        historic_fixing=historic_fixing,
        vol=vol,
    )
    return IRCapFloorModel(**{**defaults, **kwargs})


# --- Validation ---


def test_raises_if_seasoned_cap_has_no_historic_fixing():
    """start_date at/before valuation with historic_fixing=None should raise."""
    cap = make_ir_cap(start_date=dt.date(2025, 1, 1), end_date=dt.date(2027, 1, 1))
    with pytest.raises(ValueError):
        make_model(historic_fixing=None).price(cap)


# --- Pricing ---


def test_price_returns_schedule_with_cashflows():
    cap = make_ir_cap()
    schedule = make_model().price(cap)
    # TODO: assert schedule shape — how many caplets do you expect for a 2y
    # quarterly cap, and should every period carry a non-negative cashflow?
    assert ...


def test_cap_pv_is_sum_of_caplet_payoffs():
    """Total undiscounted cap amount == sum of individual caplet amounts."""
    cap = make_ir_cap()
    schedule = make_model().price(cap)
    # TODO: what is the relationship you expect between schedule.amounts and
    # the per-caplet Black-76 values? Fill in the expected aggregate.
    assert ...


def test_receive_vs_pay_caplet_direction():
    """RECEIVE -> call on the rate (cap); PAY -> put on the rate (floor)."""
    receive = make_model().price(make_ir_cap(pay_receive=PayReceive.RECEIVE))
    pay = make_model().price(make_ir_cap(pay_receive=PayReceive.PAY))
    # TODO: what relationship between the two sets of amounts encodes the
    # call-vs-put switch? (Think about which is larger when forwards > strike.)
    assert ...


# --- QuantLib validation (Tier 1 oracle) ---


def test_cap_matches_quantlib_black_engine():
    """Tier-1: caplet-by-caplet undiscounted amounts vs QuantLib BlackCapFloorEngine.

    Strategy: create one single-period QL CapFloor per caplet, price each with
    BlackCapFloorEngine using the same flat vol and discount curve, then divide
    the QL NPV by the discount factor to the payment date to recover the
    undiscounted caplet amount. Compare to schedule.amounts[i].

    Identity:
        ql_single_caplet_npv[i] / df(0, T_pay[i])  ≈  schedule.amounts[i]
    """
    ql = pytest.importorskip("QuantLib")  # noqa: F841

    DFS = [0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92]
    curve = make_ir_curve(DFS)
    cap = make_ir_cap()
    schedule = make_model(curve=curve).price(cap)  # noqa: F841

    # TODO: set the QL valuation date to match VALUATION_DATE

    # TODO: build a flat QL discount curve from the same DFS / tenors
    #   (DiscountCurve or FlatForward — your choice, but the discount factors
    #   must match exactly so the forward rates agree)

    # TODO: build the QL SOFR/IBOR index using the same curve

    # TODO: loop over schedule.accrual_start_dates and accrual_end_dates:
    #   for i, (t_start, t_end) in enumerate(zip(..., ...)):
    #       - construct a 1-period ql.CapFloor for caplet i
    #         (start=t_start, end=t_end, strike=STRIKE, notional=NOTIONAL)
    #       - attach a BlackCapFloorEngine with flat vol=VOL
    #       - ql_npv = caplet.NPV()
    #       - df_payment = curve.get_discount_factors(yearfrac to t_end)
    #       - ql_undiscounted = ql_npv / df_payment
    #       - assert ql_undiscounted == pytest.approx(schedule.amounts[i], abs=?)

    assert ...


# --- Limiting cases (Tier 2 internal correctness) ---


def test_zero_vol_collapses_to_intrinsic():
    """vol -> 0: each caplet payoff -> max(F - K, 0) (call) on the rate."""
    cap = make_ir_cap()
    schedule = make_model(vol=0.0).price(cap)  # noqa: F841
    # TODO: with vol=0 the Black-76 value is the intrinsic on each forward.
    # Reconstruct the expected per-period amounts from the curve's implied
    # forwards and assert equality.
    assert ...


def test_deep_itm_cap_approaches_forward_minus_strike():
    """Very low strike => cap behaves like paying (F - K) every period."""
    cap = make_ir_cap(strike=1e-6)
    schedule = make_model().price(cap)  # noqa: F841
    # TODO: what should each caplet amount approach as the cap goes deep ITM?
    assert ...


def test_cap_floor_parity():
    """cap(K) - floor(K) == payer-swap-style (F - K) leg, period by period."""
    cap = make_model().price(make_ir_cap(pay_receive=PayReceive.RECEIVE))  # noqa: F841
    floor = make_model().price(make_ir_cap(pay_receive=PayReceive.PAY))  # noqa: F841
    # TODO: the parity identity is independent of vol. Express the expected
    # cap.amounts - floor.amounts in terms of the forwards, strike, year
    # fractions and notional, and assert it.
    assert ...
    assert ...
