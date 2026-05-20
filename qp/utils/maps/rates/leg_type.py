from enum import StrEnum


class LegType(StrEnum):
    FIXED = "fixed"
    FLOAT = "float"
    OIS = "ois"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.lower() == member.value:
                return member

        return None
