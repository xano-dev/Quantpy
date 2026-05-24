from enum import StrEnum


class PayReceive(StrEnum):
    PAY = "PAY"
    RECEIVE = "RECEIVE"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.upper() == member.value:
                return member

        return None
