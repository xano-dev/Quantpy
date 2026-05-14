from scipy.interpolate import (
    make_interp_spline,
    CubicSpline,
    PchipInterpolator,
    Akima1DInterpolator,
)
import numpy as np
from enum import StrEnum
from functools import partial


class InterpolationMethod(StrEnum):
    LINEAR = "linear"
    LOG_LINEAR = "log_linear"
    AKIMA = "akima"
    CUBIC_SPLINE = "cubic_spline"
    MONOTONIC_CUBIC_SPLINE = "monotonic_cubic_spline"


INTERPOLATION_FN_MAP = {
    InterpolationMethod.LINEAR: partial(make_interp_spline, k=1),
    InterpolationMethod.LOG_LINEAR: partial(make_interp_spline, k=1),
    InterpolationMethod.AKIMA: Akima1DInterpolator,
    InterpolationMethod.CUBIC_SPLINE: CubicSpline,
    InterpolationMethod.MONOTONIC_CUBIC_SPLINE: PchipInterpolator,
}


class Interpolator:
    """Interpolator

    Args:
        x_values: values on the x-axis
        y_values: values on the y-axis
        interpolation_method: type of interpolation - one of linear, log_linear, akima, cubic spline, monotonic cubic spline
        extrapolate: whether the interpolation should allow extrapolation
    Example:
        >>> interpolator = Interpolator(
        ...     x_values=np.array([1,2,3,4]),
        ...     y_values=np.array([5,6,7,8]),
        ...     interpolation_method="linear",
        ...     extrapolate=False,
        ... )

        >>> interpolator.interpolate(x=2.5)
    Raises:
        ValueError: if extrapolate is false and interpolation value is outside bounds of `x_values`
    """

    def __init__(
        self,
        x_values: np.ndarray,
        y_values: np.ndarray,
        interpolation_method: InterpolationMethod,
        extrapolate: bool = False,
    ):
        self._x = x_values
        self._y = y_values
        self._interpolation_method = interpolation_method
        self._extrapolate = extrapolate

        self._catch_errors()

        self._interp_fn = self._generate_interpolator()

    @property
    def x_values(self):
        return self._x

    @property
    def y_values(self):
        return self._y

    @property
    def interpolation_method(self):
        return self._interpolation_method

    @property
    def extrapolate(self):
        return self._extrapolate

    def _catch_errors(self):
        if self._interpolation_method == InterpolationMethod.LOG_LINEAR:
            if np.any(self._y <= 0):
                raise ValueError(
                    f"One or more y values are invalid for log transformation: {self._y}"
                )

        if not np.all(np.diff(self._x) > 0):
            raise ValueError(
                f"x values should be increasing monotonically with no duplicates {self._x}"
            )

    def _generate_interpolator(self):

        match self._interpolation_method:

            case InterpolationMethod.LINEAR:
                return INTERPOLATION_FN_MAP[self._interpolation_method](
                    self._x, self._y
                )

            case InterpolationMethod.LOG_LINEAR:
                return INTERPOLATION_FN_MAP[self._interpolation_method](
                    self._x, np.log(self._y)
                )

            case _:
                return INTERPOLATION_FN_MAP[self._interpolation_method](
                    self._x, self._y, extrapolate=self._extrapolate
                )

    def interpolate(self, x: float | list[float]):
        if not self._extrapolate:
            if np.any(x < self._x[0]) or np.any(x > self._x[-1]):
                raise ValueError(f"{x} is outside interpolation range")

        if self._interpolation_method == InterpolationMethod.LOG_LINEAR:
            return np.exp(self._interp_fn(x))

        return self._interp_fn(x)
