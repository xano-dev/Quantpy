from dateutil.relativedelta import relativedelta
from enum import StrEnum


class Frequency(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semiannual"
    ANNUAL = "annual"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.lower() == member.value:
                return member
        return None


FREQUENCY_MAP = {
    Frequency.MONTHLY: relativedelta(months=1),
    Frequency.QUARTERLY: relativedelta(months=3),
    Frequency.SEMI_ANNUAL: relativedelta(months=6),
    Frequency.ANNUAL: relativedelta(months=12),
}
