import datetime as dt
from enum import StrEnum
from qp.time.holiday_helper import get_holidays
from qp.utils.maps.currencies import Currency


class Dateroll(StrEnum):
    FOLLOWING = "following"
    PRECEDING = "preceding"
    MODIFIED_FOLLOWING = "modified_following"
    MODIFIED_PRECEDING = "modified_preceding"


def compute_following(date: dt.date, hols: set[dt.date] = None) -> dt.date:

    if is_business_day(date, hols):
        return date

    rolled_date = date + dt.timedelta(days=1)

    while not is_business_day(rolled_date, hols):
        rolled_date += dt.timedelta(days=1)

    return rolled_date


def compute_preceding(date: dt.date, hols: set[dt.date] = None) -> dt.date:
    if is_business_day(date, hols):
        return date

    rolled_date = date - dt.timedelta(days=1)

    while not is_business_day(rolled_date, hols):
        rolled_date -= dt.timedelta(days=1)

    return rolled_date


def compute_modified_following(date: dt.date, hols: set[dt.date] = None) -> dt.date:
    following_bd = compute_following(date, hols)

    return (
        following_bd
        if following_bd.month == date.month
        else compute_preceding(date, hols)
    )


def compute_modified_preceding(date: dt.date, hols: set[dt.date] = None) -> dt.date:
    preceding_bd = compute_preceding(date, hols)

    return (
        preceding_bd
        if preceding_bd.month == date.month
        else compute_following(date, hols)
    )


def is_business_day(date: dt.date, hols: set[dt.date] = None) -> bool:
    day_of_week = date.weekday()

    weekend_cond = day_of_week > 4
    hol_cond = date in hols if hols is not None else False

    return not (weekend_cond or hol_cond)


def roll_day(date: dt.date, dateroll: Dateroll, currency: Currency = None):
    hols = (
        None
        if currency is None
        else get_holidays(currency, years=(date.year, date.year + 1))
    )

    dateroll_fn = DATEROLL_FN_MAP.get(dateroll)

    if dateroll_fn is None:
        raise KeyError(
            f"Error: Invalid / Unimplemented dateroll convention '{dateroll}'. Valid daycount conventions are: {list(Dateroll)}"
        )

    return dateroll_fn(date, hols)


DATEROLL_FN_MAP = {
    Dateroll.FOLLOWING: compute_following,
    Dateroll.PRECEDING: compute_preceding,
    Dateroll.MODIFIED_FOLLOWING: compute_modified_following,
    Dateroll.MODIFIED_PRECEDING: compute_modified_preceding,
}
