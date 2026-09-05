import datetime as dt

import numpy as np
import pytest
from dateutil.relativedelta import relativedelta

from qp.curves.ir_curve import IRCurve
from qp.curves.volatility.flat_vol import FlatVol
from qp.instruments.rates.ir_cap_floor import IRCapFloor
from qp.models.rates.ircapfloor_model import IRCapFloorModel
from qp.time.date.dateroll import Dateroll
from qp.time.date.daycount import Daycount
from qp.utils.maps.currency.currencies import Currency
from qp.utils.maps.general.frequencies import Frequency
from qp.utils.maps.general.payreceive import PayReceive
from qp.utils.maps.options.vol_type import VolType
from qp.utils.maps.rates.cap_floor import CapFloor
from qp.utils.maps.rates.floating_indexes import FloatingIndex

VALUATION_DATE = dt.date(2026, 6, 1)
# T+2 fixing lag off a T+2 start lands the first fixing exactly on valuation
# date, which the model treats as already fixed (inclusive <=). Start one
# business day later so every caplet's fixing is genuinely in the future.
START_DATE = dt.date(2026, 6, 4)
END_DATE_2Y = dt.date(2028, 6, 3)
NOTIONAL = 10_000_000
STRIKE = 0.05
VOL = 0.20
SHIFT = 0.03


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
        cap_floor=CapFloor.CAP,
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


def make_model(curve=None, historic_fixings=None, vol=VOL, **kwargs):
    if curve is None:
        curve = make_ir_curve([0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92])
    defaults = dict(
        valuation_date=VALUATION_DATE,
        floating_curve=curve,
        historic_fixings=historic_fixings,
        vol_obj=FlatVol(vol=vol, vol_dc_convention=Daycount.ACT_360),
    )
    return IRCapFloorModel(**{**defaults, **kwargs})


# --- Validation ---


def test_raises_if_seasoned_cap_has_no_historic_fixing():
    """start_date at/before valuation with historic_fixing=None should raise."""
    cap = make_ir_cap(start_date=dt.date(2025, 1, 1), end_date=dt.date(2027, 1, 1))
    with pytest.raises(ValueError):
        make_model(historic_fixings=None).price(cap)

# --- QuantLib validation ---


def test_cap_matches_quantlib_black_engine():
    """caplet-by-caplet undiscounted amounts vs QuantLib BlackCapFloorEngine."""
    ql = pytest.importorskip("QuantLib")

    DFS = [0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92]
    curve = make_ir_curve(DFS)
    cap = make_ir_cap()
    schedule = make_model(curve=curve).price(cap)

    ql.Settings.instance().evaluationDate = ql.Date(
        VALUATION_DATE.day, VALUATION_DATE.month, VALUATION_DATE.year
    )

    discount_factors = [1] + DFS
    dates = [
        ql.Date(date.day, date.month, date.year)
        for date in [
            VALUATION_DATE + dt.timedelta(days=tenor * 360) for tenor in curve.tenors
        ]
    ]
    day_counter = ql.Actual360()
    discount_curve = ql.DiscountCurve(dates, discount_factors, day_counter)
    discount_curve.enableExtrapolation()
    discount_handle = ql.YieldTermStructureHandle(discount_curve)

    start_date = ql.Date(START_DATE.day, START_DATE.month, START_DATE.year)
    end_date = ql.Date(END_DATE_2Y.day, END_DATE_2Y.month, END_DATE_2Y.year)

    ql_schedule = ql.Schedule(
        start_date,
        end_date,
        ql.Period(3, ql.Months),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Backward,
        False,
    )

    index = ql.IborIndex(
        "MyIndex",
        ql.Period("3m"),
        2,
        ql.USDCurrency(),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        False,
        ql.Actual360(),
        discount_handle,
    )

    ibor_leg = ql.IborLeg([NOTIONAL], ql_schedule, index)
    cap_discount = ql.Cap(ibor_leg, [STRIKE])

    volatility = ql.QuoteHandle(ql.SimpleQuote(VOL))
    engine = ql.BlackCapFloorEngine(discount_handle, volatility, ql.Actual360(), 0.0)
    cap_discount.setPricingEngine(engine)

    ql_prices = np.array(cap_discount.optionletsPrice())
    ql_discount_factors = np.array(cap_discount.optionletsDiscountFactor())
    ql_undiscounted = ql_prices / ql_discount_factors

    assert ql_undiscounted == pytest.approx(schedule.cashflows, abs=1e-6)


def test_cap_matches_quantlib_bachelier_engine():
    """caplet-by-caplet undiscounted amounts vs QuantLib's normal-vol cap engine."""
    ql = pytest.importorskip("QuantLib")  # noqa: F841

    DFS = [0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92]
    curve = make_ir_curve(DFS)
    cap = make_ir_cap()
    vol_obj = FlatVol(
        vol=VOL,
        vol_dc_convention=Daycount.ACT_360,
        vol_type=VolType.NORMAL,
    )
    schedule = make_model(curve=curve, vol_obj=vol_obj).price(cap)

    ql.Settings.instance().evaluationDate = ql.Date(
        VALUATION_DATE.day, VALUATION_DATE.month, VALUATION_DATE.year
    )

    discount_factors = [1] + DFS
    dates = [
        ql.Date(date.day, date.month, date.year)
        for date in [
            VALUATION_DATE + dt.timedelta(days=tenor * 360) for tenor in curve.tenors
        ]
    ]
    day_counter = ql.Actual360()
    discount_curve = ql.DiscountCurve(dates, discount_factors, day_counter)
    discount_curve.enableExtrapolation()
    discount_handle = ql.YieldTermStructureHandle(discount_curve)

    start_date = ql.Date(START_DATE.day, START_DATE.month, START_DATE.year)
    end_date = ql.Date(END_DATE_2Y.day, END_DATE_2Y.month, END_DATE_2Y.year)

    ql_schedule = ql.Schedule(
        start_date,
        end_date,
        ql.Period(3, ql.Months),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Backward,
        False,
    )

    index = ql.IborIndex(
        "MyIndex",
        ql.Period("3m"),
        2,
        ql.USDCurrency(),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        False,
        ql.Actual360(),
        discount_handle,
    )

    ibor_leg = ql.IborLeg([NOTIONAL], ql_schedule, index)
    cap_discount = ql.Cap(ibor_leg, [STRIKE])

    volatility = ql.ConstantOptionletVolatility(
        0, ql.NullCalendar(), ql.ModifiedFollowing, VOL, ql.Actual360(), ql.Normal
    )
    engine = ql.BachelierCapFloorEngine(
        discount_handle, ql.OptionletVolatilityStructureHandle(volatility)
    )
    cap_discount.setPricingEngine(engine)

    ql_prices = np.array(cap_discount.optionletsPrice())
    ql_discount_factors = np.array(cap_discount.optionletsDiscountFactor())
    ql_undiscounted = ql_prices / ql_discount_factors

    assert ql_undiscounted == pytest.approx(schedule.cashflows, abs=1e-6)


def test_cap_matches_quantlib_shifted_black_engine():
    """Tier-1: caplet-by-caplet undiscounted amounts vs QuantLib's shifted Black-76 cap engine (displacement != 0)."""
    ql = pytest.importorskip("QuantLib")  # noqa: F841

    DFS = [0.99, 0.98, 0.97, 0.96, 0.95, 0.94, 0.93, 0.92]
    curve = make_ir_curve(DFS)
    cap = make_ir_cap()
    vol_obj = FlatVol(
        vol=VOL,
        vol_dc_convention=Daycount.ACT_360,
        vol_type=VolType.SHIFTED_LOGNORMAL,
        displacement=SHIFT,
    )
    schedule = make_model(curve=curve, vol_obj=vol_obj).price(cap)

    ql.Settings.instance().evaluationDate = ql.Date(
        VALUATION_DATE.day, VALUATION_DATE.month, VALUATION_DATE.year
    )

    discount_factors = [1] + DFS
    dates = [
        ql.Date(date.day, date.month, date.year)
        for date in [
            VALUATION_DATE + dt.timedelta(days=tenor * 360) for tenor in curve.tenors
        ]
    ]
    day_counter = ql.Actual360()
    discount_curve = ql.DiscountCurve(dates, discount_factors, day_counter)
    discount_curve.enableExtrapolation()
    discount_handle = ql.YieldTermStructureHandle(discount_curve)

    start_date = ql.Date(START_DATE.day, START_DATE.month, START_DATE.year)
    end_date = ql.Date(END_DATE_2Y.day, END_DATE_2Y.month, END_DATE_2Y.year)

    ql_schedule = ql.Schedule(
        start_date,
        end_date,
        ql.Period(3, ql.Months),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        ql.ModifiedFollowing,
        ql.DateGeneration.Backward,
        False,
    )

    index = ql.IborIndex(
        "MyIndex",
        ql.Period("3m"),
        2,
        ql.USDCurrency(),
        ql.UnitedStates(ql.UnitedStates.NYSE),
        ql.ModifiedFollowing,
        False,
        ql.Actual360(),
        discount_handle,
    )

    ibor_leg = ql.IborLeg([NOTIONAL], ql_schedule, index)
    cap_discount = ql.Cap(ibor_leg, [STRIKE])

    volatility = ql.QuoteHandle(ql.SimpleQuote(VOL))
    engine = ql.BlackCapFloorEngine(discount_handle, volatility, ql.Actual360(), SHIFT)
    cap_discount.setPricingEngine(engine)

    ql_prices = np.array(cap_discount.optionletsPrice())
    ql_discount_factors = np.array(cap_discount.optionletsDiscountFactor())
    ql_undiscounted = ql_prices / ql_discount_factors

    assert ql_undiscounted == pytest.approx(schedule.cashflows, abs=1e-6)