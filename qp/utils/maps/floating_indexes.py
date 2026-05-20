from enum import StrEnum


class FloatingIndex(StrEnum):
    # RFRs
    SOFR = "SOFR"
    ESTR = "ESTR"
    SONIA = "SONIA"
    TONAR = "TONAR"
    SARON = "SARON"
    AONIA = "AONIA"
    CORRA = "CORRA"
    NZIONA = "NZIONA"
    NOWA = "NOWA"
    SWESTR = "SWESTR"
    HONIA = "HONIA"
    SORA = "SORA"

    # IBORs
    BBSW_1M = "BBSW_1M"
    BBSW_3M = "BBSW_3M"
    BBSW_6M = "BBSW_6M"
    BBSW_1Y = "BBSW_1Y"
    BKBM_1M = "BKBM_1M"
    BKBM_3M = "BKBM_3M"
    BKBM_6M = "BKBM_6M"
    BKBM_1Y = "BKBM_1Y"

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if value.upper() == member.value:
                return member

        return None
