from qp.utils.maps.currencies import Currency
from qp.time.daycount import Daycount

CURRENCY_DAYCOUNT: dict[Currency, Daycount] = {
    Currency.USD: Daycount.ACT_360,
    Currency.EUR: Daycount.ACT_360,
    Currency.GBP: Daycount.ACT_365,
    Currency.JPY: Daycount.ACT_365,
    Currency.CHF: Daycount.ACT_360,
    Currency.AUD: Daycount.ACT_365,
    Currency.CAD: Daycount.ACT_365,
    Currency.NZD: Daycount.ACT_365,
    Currency.NOK: Daycount.ACT_365,
    Currency.SEK: Daycount.ACT_365,
    Currency.HKD: Daycount.ACT_365,
    Currency.SGD: Daycount.ACT_365,
}
