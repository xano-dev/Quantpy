import datetime as dt
import numpy as np
import pytest
from unittest.mock import patch
from qp.curves.fx_curve import FXCurve
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
TENOR_FLOATS = [0.0, 0.25, 1.0, 2.0]
FX_RATES = [1.16, 1.171, 1.173, 1.177]


@pytest.fixture
def mock_interpolator():
    with patch("qp.curves.fx_curve.Interpolator") as mock_cls:
        yield mock_cls, mock_cls.return_value


@pytest.fixture
def curve_from_floats(mock_interpolator):
    return (
        FXCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency_1=Currency.EUR,
            currency_2=Currency.USD,
            fx_rates=FX_RATES,
            tenors=TENOR_FLOATS,
        ),
        mock_interpolator,
    )


@pytest.fixture
def curve_from_dates(mock_interpolator):
    with patch("qp.curves.fx_curve.yearfrac", return_value=np.array(TENOR_FLOATS)):
        curve = FXCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency_1=Currency.EUR,
            currency_2=Currency.USD,
            fx_rates=FX_RATES,
            tenors=TENOR_DATES,
        )
    return curve, mock_interpolator


# ---- Properties ----


def test_properties(curve_from_floats):
    curve, _ = curve_from_floats
    assert curve.at_date == AT_DATE
    assert curve.daycount == Daycount.ACT_360
    assert curve.currency_1 == Currency.EUR
    assert curve.currency_2 == Currency.USD
    assert np.array_equal(curve.fx_rates, np.array(FX_RATES))
    assert curve.interpolation_method == InterpolationMethod.LOG_LINEAR
    assert curve.extrapolate is False


def test_spot_rate(curve_from_floats):
    curve, _ = curve_from_floats
    assert curve.spot_rate == 1.16


# ---- Tenor handling ----


def test_float_tenors_stored_as_is(curve_from_floats):
    curve, _ = curve_from_floats
    assert np.array_equal(curve.tenors, np.array(TENOR_FLOATS))


def test_date_tenors_converted_via_yearfrac():
    with patch("qp.curves.fx_curve.Interpolator"):
        with patch(
            "qp.curves.fx_curve.yearfrac", return_value=np.array(TENOR_FLOATS)
        ) as mock_yf:
            FXCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency_1=Currency.EUR,
                currency_2=Currency.USD,
                fx_rates=FX_RATES,
                tenors=TENOR_DATES,
            )
            mock_yf.assert_called_once_with(
                AT_DATE, TENOR_DATES, Daycount.ACT_360, Currency.EUR, Currency.USD
            )


def test_date_tenors_stored_as_yearfracs(curve_from_dates):
    curve, _ = curve_from_dates
    np.testing.assert_allclose(curve.tenors, TENOR_FLOATS)


# ---- Interpolator construction ----


def test_interpolator_constructed_with_correct_args(curve_from_floats):
    _, (mock_cls, _) = curve_from_floats
    call_args = mock_cls.call_args
    np.testing.assert_allclose(call_args[0][0], np.array(TENOR_FLOATS))
    np.testing.assert_allclose(call_args[0][1], np.array(FX_RATES))
    assert call_args[0][2] == InterpolationMethod.LOG_LINEAR
    assert call_args[0][3] is False


def test_get_rate_delegates_to_interpolator(curve_from_floats):
    curve, (_, mock_instance) = curve_from_floats
    mock_instance.interpolate.return_value = 1.165
    assert curve.get_rates(0.1) == 1.165
    mock_instance.interpolate.assert_called_once_with(0.1)


# ---- Validation ----


def test_raises_if_first_tenor_not_zero():
    with patch("qp.curves.fx_curve.Interpolator"):
        with pytest.raises(ValueError, match="must be a spot FX rate"):
            FXCurve(
                at_date=AT_DATE,
                daycount=Daycount.ACT_360,
                currency_1=Currency.EUR,
                currency_2=Currency.USD,
                fx_rates=FX_RATES,
                tenors=[0.25, 0.5, 1.0, 2.0],
            )


def test_non_default_interpolation_method():
    with patch("qp.curves.fx_curve.Interpolator"):
        curve = FXCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency_1=Currency.EUR,
            currency_2=Currency.USD,
            fx_rates=FX_RATES,
            tenors=TENOR_FLOATS,
            interpolation_method=InterpolationMethod.LINEAR,
        )
        assert curve.interpolation_method == InterpolationMethod.LINEAR


def test_extrapolate_flag():
    with patch("qp.curves.fx_curve.Interpolator"):
        curve = FXCurve(
            at_date=AT_DATE,
            daycount=Daycount.ACT_360,
            currency_1=Currency.EUR,
            currency_2=Currency.USD,
            fx_rates=FX_RATES,
            tenors=TENOR_FLOATS,
            extrapolate=True,
        )
        assert curve.extrapolate is True


def run_tests():
    pytest.main([__file__, "-v"])
