from functools import lru_cache
import datetime as dt
import holidays

@lru_cache(maxsize=None)
def get_holidays(currency: str, years: tuple[int]) -> set[dt.date]:
    return set(holidays.country_holidays(country=HOL_MAP.get(currency), years=years).keys())

HOL_MAP = {
    "USD": "US",
    "EUR": "XECB",
    "GBP": "GB",
    "JPY": "JP",
    "CHF": "CH",
    "AUD": "AU",
    "CAD": "CA",
    "NZD": "NZ",
    "NOK": "NO",
    "SEK": "SE",
    "HKD": "HK",
    "SGD": "SG",
}