import pytest
from qp.utils.math.interpolation import Interpolator, InterpolationMethod
import numpy as np

X = np.array([1, 2, 3, 4, 5])
Y = np.array([1, 4, 30, 16, 25])
Y_EXP = np.exp(X)
Y_ZERO = np.array([0, 4, 9, 16, 25])
Y_NEGATIVE = np.array([-1, 4, 9, 16, 25])

# ---- Test Inputs ----


def test_X_input():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, False)
    assert np.array_equal(interpolator.x_values, X) is True


def test_Y_input():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, False)
    assert np.array_equal(interpolator.y_values, Y) is True


def test_method_input():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, False)
    assert interpolator.interpolation_method == InterpolationMethod.LINEAR


def test_extrapolate_input():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, False)
    assert interpolator.extrapolate is False


# ---- Test Extrapolation Guard ----


def test_extrapolate_false():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, False)
    with pytest.raises(ValueError):
        interpolator.interpolate(100)


def test_extrapolate_true():
    interpolator: Interpolator = Interpolator(X, Y, InterpolationMethod.LINEAR, True)
    assert interpolator.interpolate(100) == 880


# ---- Test Log guard ----


def test_log_guard_zero():
    with pytest.raises(ValueError):
        interpolator: Interpolator = Interpolator(
            X, Y_ZERO, InterpolationMethod.LOG_LINEAR, True
        )


def test_log_guard_negative():
    with pytest.raises(ValueError):
        interpolator: Interpolator = Interpolator(
            X, Y_NEGATIVE, InterpolationMethod.LOG_LINEAR, True
        )


# ---- Test knot points ----


@pytest.mark.parametrize(
    "input_val, expected, method",
    [
        (1, 1, InterpolationMethod.LINEAR),
        (2, 4, InterpolationMethod.LOG_LINEAR),
        (3, 30, InterpolationMethod.CUBIC_SPLINE),
        (4, 16, InterpolationMethod.MONOTONIC_CUBIC_SPLINE),
        (5, 25, InterpolationMethod.AKIMA),
    ],
)
def test_knot_point(input_val, expected, method):
    interpolator: Interpolator = Interpolator(X, Y, method, True)

    assert interpolator.interpolate(input_val) == pytest.approx(expected)


# ---- Test unsorted and duplicate x values ----


def test_unsorted_x():
    with pytest.raises(ValueError):
        interpolator: Interpolator = Interpolator(
            np.array([3, 1, 4, 5]), Y, InterpolationMethod.LINEAR, True
        )


def test_duplicate_x():
    with pytest.raises(ValueError):
        interpolator: Interpolator = Interpolator(
            np.array([3, 1, 4, 5]), Y, InterpolationMethod.LINEAR, True
        )


# ---- Test methods ----


@pytest.mark.parametrize(
    "input_val, expected, method",
    [
        (2.5, 13.737297, InterpolationMethod.LINEAR),
        (2.5, 12.182494, InterpolationMethod.LOG_LINEAR),
        (2.5, 12.242429, InterpolationMethod.CUBIC_SPLINE),
        (2.5, 12.270481, InterpolationMethod.MONOTONIC_CUBIC_SPLINE),
        (2.5, 12.678820, InterpolationMethod.AKIMA),
    ],
)
def test_methods(input_val, expected, method):
    interpolator: Interpolator = Interpolator(X, Y_EXP, method, True)

    assert interpolator.interpolate(input_val) == pytest.approx(expected)
