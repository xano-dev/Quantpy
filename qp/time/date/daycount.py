import pandas as pd
import datetime as dt
import numpy as np
from enum import StrEnum
from qp.time.date.holiday_helper import get_holidays
from qp.utils.maps.currency.currencies import Currency


class Daycount(StrEnum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    THIRTY_360 = "30/360"
    THIRTY_365 = "30/365"
    BUS_252 = "BUS/252"


# --- Scalar helpers ---


def get_thirty_days(start: dt.date, end: dt.date, denom: int) -> float:
    total_year_days = (end.year - start.year) * denom
    total_month_days = (end.month - start.month) * 30
    start_day = start.day
    end_day = end.day

    if start_day == 31:
        start_day = 30

    if end_day == 31 and (start_day == 31 or start_day == 30):
        end_day = 30

    return total_year_days + total_month_days - start_day + end_day


def get_actual_days(start: dt.date, end: dt.date) -> float:
    return (end - start).days


def act_360(start: dt.date, end: dt.date) -> float:
    return get_actual_days(start, end) / 360


def act_365(start: dt.date, end: dt.date) -> float:
    return get_actual_days(start, end) / 365


def thirty_360(start: dt.date, end: dt.date) -> float:
    return get_thirty_days(start, end, 360) / 360


def thirty_365(start: dt.date, end: dt.date) -> float:
    return get_thirty_days(start, end, 365) / 365


def bus_252(start: dt.date, end: dt.date, hols: set[dt.date]) -> float:
    return (
        len(pd.bdate_range(start, end, freq="C", holidays=hols, inclusive="left")) / 252
    )


# --- Vectorised helpers ---


def get_thirty_days_vec(starts: dt.date, ends: np.ndarray, denom: int) -> int:

    end_years = ends.astype("datetime64[Y]").astype(int) + 1970
    end_months = ends.astype("datetime64[M]").astype(int) % 12 + 1
    end_days = (ends - ends.astype("datetime64[M]")).astype(int) + 1

    if isinstance(starts, dt.date):
        start_years = starts.year
        start_months = starts.month
        start_days = 30 if starts.day == 31 else starts.day
    else:
        start_years = starts.astype("datetime64[Y]").astype(int) + 1970
        start_months = starts.astype("datetime64[M]").astype(int) % 12 + 1
        start_day_raw = (starts - starts.astype("datetime64[M]")).astype(int) + 1
        start_days = np.where(start_day_raw == 31, 30, start_day_raw)

    total_year_days = (end_years - start_years) * denom
    total_month_days = (end_months - start_months) * 30

    end_days = np.where(
        (end_days == 31) & ((start_days == 30) | (start_days == 31)), 30, end_days
    )

    thirty_days = total_year_days + total_month_days - start_days + end_days

    return thirty_days


def get_actual_days_vec(start: dt.date | np.ndarray, ends: np.ndarray) -> np.ndarray:
    starts = (
        np.datetime64(start, "D")
        if isinstance(start, dt.date)
        else np.array(start, dtype="datetime64[D]")
    )
    return (ends - starts).astype(int)


def act_360_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_actual_days_vec(start, ends) / 360


def act_365_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_actual_days_vec(start, ends) / 365


def thirty_360_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_thirty_days_vec(start, ends, 360) / 360


def thirty_365_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_thirty_days_vec(start, ends, 365) / 365


def bus_252_vec(
    starts: dt.date | np.ndarray, ends: np.ndarray, hols: set[dt.date]
) -> np.ndarray:
    hols = np.array(sorted(hols), dtype="datetime64[D]")
    return np.busday_count(starts, ends, holidays=hols) / 252


def yearfrac(
    start: dt.date | list[dt.date] | np.ndarray,
    end: dt.date | list[dt.date] | np.ndarray,
    daycount: Daycount,
    currency_1: Currency = None,
    currency_2: Currency = None,
) -> float | np.ndarray:
    is_scalar = isinstance(start, dt.date) and isinstance(end, dt.date)

    ends = end if is_scalar else np.array(end, dtype="datetime64[D]")
    starts = start if is_scalar else np.array(start, dtype="datetime64[D]")

    # holiday range must cover every start and end year
    if is_scalar:
        min_year = start.year
        max_year = end.year
    else:
        end_dates = np.array(end, dtype="datetime64[D]")
        start_dates = np.array(start, dtype="datetime64[D]")
        min_year = int(start_dates.astype("datetime64[Y]").astype(int).min()) + 1970
        max_year = int(end_dates.astype("datetime64[Y]").astype(int).max()) + 1970

    def _get_currency_hols(currency):
        return (
            None
            if currency is None
            else get_holidays(currency, years=tuple(range(min_year, max_year + 1)))
        )

    hols = (_get_currency_hols(currency_1) or set()).union(
        _get_currency_hols(currency_2) or set()
    )

    yearfrac_fn = (
        SCALAR_DAYCOUNT_FN_MAP.get(daycount)
        if is_scalar
        else VEC_DAYCOUNT_FN_MAP.get(daycount)
    )

    if yearfrac_fn is None:
        raise KeyError(
            f"Error: Invalid / Unimplemented daycount convention '{daycount}'. "
            f"Valid daycount conventions are: {list(Daycount)}"
        )

    if daycount == Daycount.BUS_252:
        return yearfrac_fn(starts, ends, hols)

    return yearfrac_fn(starts, ends)


SCALAR_DAYCOUNT_FN_MAP = {
    Daycount.ACT_360: act_360,
    Daycount.ACT_365: act_365,
    Daycount.THIRTY_360: thirty_360,
    Daycount.THIRTY_365: thirty_365,
    Daycount.BUS_252: bus_252,
}

VEC_DAYCOUNT_FN_MAP = {
    Daycount.ACT_360: act_360_vec,
    Daycount.ACT_365: act_365_vec,
    Daycount.THIRTY_360: thirty_360_vec,
    Daycount.THIRTY_365: thirty_365_vec,
    Daycount.BUS_252: bus_252_vec,
}
