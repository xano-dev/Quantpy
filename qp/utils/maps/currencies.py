from enum import StrEnum


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"
    AUD = "AUD"
    CAD = "CAD"
    NZD = "NZD"
    NOK = "NOK"
    SEK = "SEK"
    HKD = "HKD"
    SGD = "SGD"

    @classmethod
    def _missing_(cls, value):
        return cls(value.upper())
