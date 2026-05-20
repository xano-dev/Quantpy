from enum import StrEnum


class BuySell(StrEnum):
    BUY = "buy"
    SELL = "sell"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.lower() == member.value:
                return member

        return None
