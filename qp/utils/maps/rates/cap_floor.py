from enum import StrEnum


class CapFloor(StrEnum):
    CAP = "cap"
    FLOOR = "floor"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.lower() == member.value:
                return member

        return None
