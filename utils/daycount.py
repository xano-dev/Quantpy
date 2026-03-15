import pandas as pd
import datetime as dt
import enum


class Daycount(enum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    THIRTY_360 = "30/360"
    THIRTY_365 = "30/365"
    BUS_252 = "BUS/252"


def get_thirty_days():
    pass

def get_actual_days():
    pass

def act_360():
    pass

def act_365():
    pass

def thirty_360():
    pass

def thirty_365():
    pass

def bus_252():
    pass

def yearfrac(start: dt.date, end: dt.date, daycount: Daycount):
    yearfrac_fn = DAYCOUNT_FN_MAP.get(Daycount[daycount])
    pass

DAYCOUNT_FN_MAP = {
    "ACT/360": act_360,
    "ACT/365": act_365,
    "30/360": thirty_360,
    "30/365": thirty_365,
    "BUS/252": bus_252
}