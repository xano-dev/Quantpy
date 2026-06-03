from enum import StrEnum


class CallPut(StrEnum):
    CALL = "call"
    PUT = "put"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member == value.lower():
                return member

        return None
