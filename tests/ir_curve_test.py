import datetime as dt
import numpy as np
import pytest
import warnings
from unittest.mock import patch
from qp.curves.ir_curve import IRCurve
from qp.time.daycount import Daycount
from qp.utils.maps.currencies import Currency
from qp.utils.math.interpolation import InterpolationMethod

AT_DATE = dt.date(2026, 5, 14)
TENOR_DATES = [
    dt.date(2026, 5, 14),
    dt.date(2026, 8, 14),
    dt.date(2027, 5, 14),
    dt.date(2028, 5, 14),
]
TENOR_FLOATS = np.array([0.0, 0.25, 1.0, 2.0])
INTEREST_RATES = np.array([0.0, 0.045, 0.05, 0.052])
DISCOUNT_FACTORS = np.exp(-INTEREST_RATES * TENOR_FLOATS)
CURVE_NAME = "USD_SOFR"


@pytest.fixture
def mock_interpolator():
    with patch("qp.curves.ir_curve.Interpolator") as mock_cls:
        yield mock_cls, mock_cls.return_value


@pytest.fixture
def curve_from_rates(mock_interpolator):
    return (
        IRCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency=Currency.USD,
            curve_name=CURVE_NAME,
            tenors=TENOR_FLOATS,
            interest_rates=INTEREST_RATES,
        ),
        mock_interpolator,
    )


@pytest.fixture
def curve_from_dfs(mock_interpolator):
    return (
        IRCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency=Currency.USD,
            curve_name=CURVE_NAME,
            tenors=TENOR_FLOATS,
            discount_factors=DISCOUNT_FACTORS,
        ),
        mock_interpolator,
    )


@pytest.fixture
def curve_from_dates(mock_interpolator):
    with patch("qp.curves.ir_curve.yearfrac", return_value=TENOR_FLOATS):
        curve = IRCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency=Currency.USD,
            curve_name=CURVE_NAME,
            tenors=TENOR_DATES,
            interest_rates=INTEREST_RATES,
        )
    return curve, mock_interpolator


# ---- Properties ----


def test_properties(curve_from_rates):
    curve, _ = curve_from_rates
    assert curve.at_date == AT_DATE
    assert curve.daycount == Daycount.ACT_360
    assert curve.currency == Currency.USD
    assert curve.curve_name == CURVE_NAME
    assert curve.interpolation_method == InterpolationMethod.LOG_LINEAR
    assert curve.extrapolate is False


def test_interest_rates_stored(curve_from_rates):
    curve, _ = curve_from_rates
    np.testing.assert_allclose(curve.interest_rates, INTEREST_RATES)


def test_discount_factors_stored(curve_from_dfs):
    curve, _ = curve_from_dfs
    np.testing.assert_allclose(curve.discount_factors, DISCOUNT_FACTORS)


def test_tenors_stored(curve_from_rates):
    curve, _ = curve_from_rates
    np.testing.assert_allclose(curve.tenors, TENOR_FLOATS)


# ---- Raises if neither rates nor dfs provided ----


def test_raises_if_no_rates_or_dfs():
    with patch("qp.curves.ir_curve.Interpolator"):
        with pytest.raises(ValueError, match="Must pass at least one"):
            IRCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency=Currency.USD,
                curve_name=CURVE_NAME,
                tenors=TENOR_FLOATS,
            )


# ---- Derived values ----


def test_discount_factors_derived_from_rates(curve_from_rates):
    # DFs should be derived as exp(-r * t) when only rates are provided
    curve, _ = curve_from_rates
    expected = np.exp(-INTEREST_RATES * TENOR_FLOATS)
    np.testing.assert_allclose(curve.discount_factors, expected)


def test_rates_derived_from_discount_factors(curve_from_dfs):
    # Rates should be derived as -log(df) / t when only DFs are provided
    curve, _ = curve_from_dfs
    # skip tenor 0 to avoid division by zero
    np.testing.assert_allclose(curve.interest_rates[1:], INTEREST_RATES[1:])


# ---- Tenor handling ----


def test_date_tenors_converted_via_yearfrac():
    with patch("qp.curves.ir_curve.Interpolator"):
        with patch("qp.curves.ir_curve.yearfrac", return_value=TENOR_FLOATS) as mock_yf:
            IRCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency=Currency.USD,
                curve_name=CURVE_NAME,
                tenors=TENOR_DATES,
                interest_rates=INTEREST_RATES,
            )
            mock_yf.assert_called_once_with(
                AT_DATE, TENOR_DATES, Daycount.ACT_360, Currency.USD
            )


def test_date_tenors_stored_as_yearfracs(curve_from_dates):
    curve, _ = curve_from_dates
    np.testing.assert_allclose(curve.tenors, TENOR_FLOATS)


# ---- Auto-insertion of tenor 0 and DF 1 ----


def test_warns_and_inserts_zero_tenor():
    with patch("qp.curves.ir_curve.Interpolator"):
        with pytest.warns(UserWarning, match="first tenor"):
            curve = IRCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency=Currency.USD,
                curve_name=CURVE_NAME,
                tenors=np.array([0.25, 1.0, 2.0]),
                interest_rates=np.array([0.045, 0.05, 0.052]),
            )
        assert curve.tenors[0] == 0.0


def test_warns_and_inserts_unit_df():
    with patch("qp.curves.ir_curve.Interpolator"):
        dfs = np.array([0.989, 0.952, 0.903])
        with pytest.warns(UserWarning, match="first discount factor"):
            curve = IRCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency=Currency.USD,
                curve_name=CURVE_NAME,
                tenors=np.array([0.25, 1.0, 2.0]),
                discount_factors=dfs,
            )
        assert curve.discount_factors[0] == 1.0


# ---- Interpolator construction ----


def test_interpolator_constructed_with_correct_args(curve_from_rates):
    _, (mock_cls, _) = curve_from_rates
    call_args = mock_cls.call_args
    np.testing.assert_allclose(call_args[0][0], TENOR_FLOATS)
    np.testing.assert_allclose(call_args[0][1], DISCOUNT_FACTORS)
    assert call_args[0][2] == InterpolationMethod.LOG_LINEAR
    assert call_args[0][3] is False


# ---- get_discount_factors and get_rates ----


def test_get_discount_factors_delegates_to_interpolator(curve_from_rates):
    curve, (_, mock_instance) = curve_from_rates
    mock_instance.interpolate.return_value = 0.95
    assert curve.get_discount_factors(1.0) == 0.95
    mock_instance.interpolate.assert_called_once_with(1.0)


def test_get_rates_derived_from_interpolator(curve_from_rates):
    curve, (_, mock_instance) = curve_from_rates
    mock_instance.interpolate.return_value = np.exp(-0.05 * 1.0)
    result = curve.get_rates(1.0)
    assert result == pytest.approx(0.05)


# ---- rate_type = Yield raises NotImplementedError ----


def test_yield_rate_type_raises_not_implemented():
    with patch("qp.curves.ir_curve.Interpolator"):
        with pytest.raises(NotImplementedError):
            IRCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency=Currency.USD,
                curve_name=CURVE_NAME,
                tenors=TENOR_FLOATS,
                interest_rates=INTEREST_RATES,
                rate_type="Yield",
            )


# ---- Non-default options ----


def test_non_default_interpolation_method():
    with patch("qp.curves.ir_curve.Interpolator"):
        curve = IRCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency=Currency.USD,
            curve_name=CURVE_NAME,
            tenors=TENOR_FLOATS,
            interest_rates=INTEREST_RATES,
            interpolation_method=InterpolationMethod.LINEAR,
        )
        assert curve.interpolation_method == InterpolationMethod.LINEAR


def test_extrapolate_flag():
    with patch("qp.curves.ir_curve.Interpolator"):
        curve = IRCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency=Currency.USD,
            curve_name=CURVE_NAME,
            tenors=TENOR_FLOATS,
            interest_rates=INTEREST_RATES,
            extrapolate=True,
        )
        assert curve.extrapolate is True


def run_tests():
    pytest.main([__file__, "-v"])
