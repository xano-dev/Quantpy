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
        for member in cls:
            if value.upper() == member.value:
                return member

        return None
