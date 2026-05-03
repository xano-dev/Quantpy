from functools import lru_cache
import datetime as dt
import holidays
from qp.utils.maps.hol_map import HOL_MAP
from qp.utils.maps.currencies import Currency

@lru_cache(maxsize=None)
def get_holidays(currency: Currency, years: tuple[int]) -> set[dt.date]:
    return set(holidays.country_holidays(country=HOL_MAP.get(currency), years=years).keys())
