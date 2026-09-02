from enum import StrEnum


class VolType(StrEnum):
    SHIFTED_LOGNORMAL = "shifted_lognormal"
    NORMAL = "normal"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member == value.lower():
                return member

        return None
