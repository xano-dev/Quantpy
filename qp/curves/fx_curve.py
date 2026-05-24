from qp.utils.math.interpolation import InterpolationMethod, Interpolator
from qp.time.date.daycount import Daycount, yearfrac
from qp.utils.maps.currency.currencies import Currency
import datetime as dt
import numpy as np


class FXCurve:
    """Python representation of an FX rate curve for a currency pair.

    Tenors can be provided as dates or year fractions. If dates are provided,
    they are converted to year fractions using the specified daycount convention.
    The first tenor must always be 0, corresponding to the spot FX rate.

    Args:
        at_date: curve valuation date
        daycount: daycount convention used for year fraction calculations
        currency_1: first currency of the pair
        currency_2: second currency of the pair
        fx_rates: FX rates corresponding to each tenor, quoted as currency_2/currency_1
        tenors: tenor dates or year fractions - first entry must be spot (0)
        interpolation_method: interpolation method to use - default is log-linear
        extrapolate: whether to allow extrapolation beyond the curve's tenor range

    Example:
        >>> curve = FXCurve(
        ...     at_date=dt.date(2026, 5, 14),
        ...     daycount=Daycount.ACT_360,
        ...     currency_1=Currency.EUR,
        ...     currency_2=Currency.USD,
        ...     fx_rates=[1.16, 1.171, 1.173, 1.177],
        ...     tenors=[dt.date(2026, 5, 14), dt.date(2026, 8, 14), dt.date(2027, 5, 14), dt.date(2028, 5, 14)],
        ... )
    """

    def __init__(
        self,
        at_date: dt.date,
        daycount: Daycount,
        currency_1: Currency,
        currency_2: Currency,
        fx_rates: list[float] | np.ndarray,
        tenors: list[dt.date] | list[float] | np.ndarray,
        interpolation_method: InterpolationMethod = InterpolationMethod.LOG_LINEAR,
        extrapolate: bool = False,
    ):
        self._at_date = at_date
        self._daycount = daycount
        self._currency_1 = currency_1
        self._currency_2 = currency_2
        self._fx_rates = np.array(fx_rates)

        if all(isinstance(item, dt.date) for item in tenors):
            self._tenors = self._get_tenors(tenors)
        else:
            self._tenors = np.array(tenors)

        self._catch_errors()

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
    def currency_1(self):
        return self._currency_1

    @property
    def currency_2(self):
        return self._currency_2

    @property
    def fx_rates(self):
        return self._fx_rates

    @property
    def tenors(self):
        return self._tenors

    @property
    def interpolation_method(self):
        return self._interpolation_method

    @property
    def extrapolate(self):
        return self._extrapolate

    @property
    def spot_rate(self):
        return self._fx_rates[0]

    def _catch_errors(self):
        if self._tenors[0] != 0:
            raise ValueError(
                f"First tenor is {self._tenors[0]} - must be a spot FX rate (i.e. tenor = 0)"
            )

    def _get_tenors(self, tenors: list[dt.date]):
        return yearfrac(
            self.at_date, tenors, self._daycount, self._currency_1, self._currency_2
        )

    def _generate_interpolator(self):
        return Interpolator(
            self._tenors,
            self._fx_rates,
            self._interpolation_method,
            self._extrapolate,
        )

    def get_rates(self, tenor: float | np.ndarray | dt.date) -> float:
        if isinstance(tenor, dt.date):
            tenor = yearfrac(self.at_date, tenor, self._daycount)
        return self._interpolator.interpolate(tenor)
