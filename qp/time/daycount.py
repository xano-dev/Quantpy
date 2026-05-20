import pandas as pd
import datetime as dt
import numpy as np
from enum import StrEnum
from qp.time.holiday_helper import get_holidays
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


def get_thirty_days_vec(start: dt.date, ends: np.ndarray, denom: int) -> int:

    years = ends.astype("datetime64[Y]").astype(int) + 1970
    months = ends.astype("datetime64[M]").astype(int) % 12 + 1
    days = (ends - ends.astype("datetime64[M]")).astype(int) + 1

    total_year_days = (years - start.year) * denom
    total_month_days = (months - start.month) * 30
    start_day = 30 if start.day == 31 else start.day
    end_day = np.where((days == 31) & ((start_day == 30) | (start_day == 31)), 30, days)

    thirty_days = total_year_days + total_month_days - start_day + end_day

    return thirty_days


def get_actual_days_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return (ends - np.datetime64(start, "D")).astype(int)


def act_360_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_actual_days_vec(start, ends) / 360


def act_365_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_actual_days_vec(start, ends) / 365


def thirty_360_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_thirty_days_vec(start, ends, 360) / 360


def thirty_365_vec(start: dt.date, ends: np.ndarray) -> np.ndarray:
    return get_thirty_days_vec(start, ends, 365) / 365


def bus_252_vec(start: dt.date, ends: np.ndarray, hols: set[dt.date]) -> np.ndarray:
    hols = np.array(sorted(hols), dtype="datetime64[D]")
    return np.busday_count(start, ends, holidays=hols) / 252


def yearfrac(
    start: dt.date,
    end: dt.date | list[dt.date] | np.ndarray,
    daycount: Daycount,
    currency_1: Currency = None,
    currency_2: Currency = None,
) -> float | np.ndarray:
    is_scalar = isinstance(end, dt.date)
    max_year = end.year if is_scalar else max(end).year
    ends = end if is_scalar else np.array(end, dtype="datetime64[D]")

    def _get_currency_hols(currency):
        return (
            None
            if currency is None
            else get_holidays(currency, years=tuple(range(start.year, max_year + 1)))
        )

    currency_1_hols = _get_currency_hols(currency_1)
    currency_2_hols = _get_currency_hols(currency_2)

    hols = (currency_1_hols or set()).union(currency_2_hols or set())

    yearfrac_fn = (
        SCALAR_DAYCOUNT_FN_MAP.get(daycount)
        if is_scalar
        else VEC_DAYCOUNT_FN_MAP.get(daycount)
    )

    if yearfrac_fn is None:
        raise KeyError(
            f"Error: Invalid / Unimplemented daycount convention '{daycount}'. Valid daycount conventions are: {list(Daycount)}"
        )

    # business days needs holidays
    if daycount == Daycount.BUS_252:
        return yearfrac_fn(start, ends, hols)

    return yearfrac_fn(start, ends)


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
