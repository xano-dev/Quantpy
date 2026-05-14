from qp.utils.math.interpolation import InterpolationMethod, Interpolator
from qp.time.daycount import Daycount, yearfrac
from qp.utils.maps.currencies import Currency
from qp.utils.bootstrapper.bootstrap import bootstrap
import datetime as dt
import numpy as np
from typing import Literal
import warnings


class IRCurve:
    """Python representation of an interest rate curve for a single currency.

    Tenors can be provided as dates or year fractions. If dates are provided,
    they are converted to year fractions using the specified daycount convention.
    Either interest rates or discount factors must be provided — if one is given,
    the other is derived. If the first tenor is not zero, or the first discount
    factor is not one, they are inserted automatically with a warning.

    Args:
        at_date: curve valuation date
        daycount: daycount convention used for year fraction calculations
        currency: currency of the interest rate curve
        curve_name: name of the curve, e.g. "USD_SOFR"
        tenors: tenor dates or year fractions
        interpolation_method: interpolation method to use - default is log-linear
        interest_rates: zero rates corresponding to each tenor - derived from discount factors if not provided
        discount_factors: discount factors corresponding to each tenor - derived from interest rates if not provided
        extrapolate: whether to allow extrapolation beyond the curve's tenor range
        rate_type: whether interest rates are zero rates or yield (par) rates - yield rates are bootstrapped to zero rates internally, see `boostrap()` for details

    Example:
        >>> curve = IRCurve(
        ...     at_date=dt.date(2026, 5, 14),
        ...     daycount=Daycount.ACT_360,
        ...     currency=Currency.USD,
        ...     curve_name="USD_SOFR",
        ...     tenors=[0.0, 0.25, 0.5, 1.0, 2.0],
        ...     interest_rates=[0.0, 0.045, 0.047, 0.05, 0.052],
        ... )
    """

    def __init__(
        self,
        at_date: dt.date,
        daycount: Daycount,
        currency: Currency,
        curve_name: str,
        tenors: list[dt.date] | list[float] | np.ndarray,
        interpolation_method: InterpolationMethod = InterpolationMethod.LOG_LINEAR,
        interest_rates: list[float] | np.ndarray | None = None,
        discount_factors: list[float] | np.ndarray | None = None,
        extrapolate: bool = False,
        rate_type: Literal["Zero", "Yield"] = "Zero",
    ):
        if interest_rates is None and discount_factors is None:
            raise ValueError(
                "Must pass at least one of interest rates or discount factors"
            )

        self._at_date = at_date
        self._daycount = daycount
        self._currency = currency
        self._curve_name = curve_name

        if all(isinstance(item, dt.date) for item in tenors):
            self._tenors = self._get_tenors(tenors)
        else:
            self._tenors = np.array(tenors)

        self._interest_rates = self._generate_interest_rates(
            interest_rates, discount_factors, rate_type
        )
        self._discount_factors = self._generate_discount_factors(
            interest_rates, discount_factors
        )

        self._ensure_correct_tenors_dfs()

        if len(self._discount_factors) != len(self._tenors):
            raise ValueError(
                f"Lengths of tenors {len(self._tenors)} and discount factors {len(self._discount_factors)} are unequal - only tenor of zero or discount factor of one was inserted"
            )

        self._interpolation_method = interpolation_method
        self._extrapolate = extrapolate
        self._interpolator = self._generate_interpolator()

    @property
    def at_date(self):
        return self._at_date

    @property
    def daycount(self):
        return self._daycount

    @property
    def currency(self):
        return self._currency

    @property
    def curve_name(self):
        return self._curve_name

    @property
    def interest_rates(self):
        return self._interest_rates

    @property
    def discount_factors(self):
        return self._discount_factors

    @property
    def tenors(self):
        return self._tenors

    @property
    def interpolation_method(self):
        return self._interpolation_method

    @property
    def extrapolate(self):
        return self._extrapolate

    def _get_tenors(self, tenors: list[dt.date]):
        return np.array(yearfrac(self.at_date, tenors, self._daycount, self._currency))

    def _generate_interpolator(self):
        return Interpolator(
            self._tenors,
            self._discount_factors,
            self._interpolation_method,
            self._extrapolate,
        )

    def _generate_discount_factors(
        self, interest_rates: np.ndarray, discount_factors: np.ndarray
    ) -> np.ndarray:

        dfs = (
            discount_factors
            if discount_factors is not None
            else np.exp(-interest_rates * self._tenors)
        )

        return np.array(dfs)

    def _generate_interest_rates(
        self,
        interest_rates: np.ndarray,
        discount_factors: np.ndarray,
        rate_type: Literal["Zero", "Yield"],
    ) -> np.ndarray:

        interest_rates = (
            interest_rates
            if rate_type == "Zero"
            else self._bootstrap_rates(interest_rates)
        )

        rates = (
            interest_rates
            if interest_rates is not None
            else np.divide(
                -np.log(discount_factors),
                self._tenors,
                where=(self._tenors != 0),
                out=np.full(len(discount_factors), np.nan),
            )
            # else -np.log(discount_factors) / self._tenors
        )

        return np.array(rates)

    def _bootstrap_rates(self, interest_rates: np.ndarray):
        raise NotImplementedError("Bootstrapper not yet implemented")

    def _ensure_correct_tenors_dfs(self):
        if self._tenors[0] != 0:
            warnings.warn(
                f"WARNING: first tenor is {self._tenors[0]} (not zero), inserting zero as first tenor"
            )
            self._tenors = np.insert(self._tenors, 0, 0)

        if self._discount_factors[0] != 1:
            warnings.warn(
                f"WARNING: first discount factor is {self._discount_factors[0]} (not one), inserting one as first discount factor"
            )
            self._discount_factors = np.insert(self._discount_factors, 0, 1)

    def get_discount_factors(self, tenors: float | np.ndarray) -> float | np.ndarray:
        return self._interpolator.interpolate(tenors)

    def get_rates(self, tenors: float | np.ndarray) -> float | np.ndarray:
        return -np.log(self._interpolator.interpolate(tenors)) / tenors
