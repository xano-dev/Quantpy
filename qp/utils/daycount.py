import pandas as pd
import datetime as dt
from enum import StrEnum
from qp.utils.holiday_helper import get_holidays

class Daycount(StrEnum):
    ACT_360 = "ACT/360"
    ACT_365 = "ACT/365"
    THIRTY_360 = "30/360"
    THIRTY_365 = "30/365"
    BUS_252 = "BUS/252"


def get_thirty_days(start: dt.date, end: dt.date, denom: int):
    total_year_days = (end.year - start.year) * denom 
    total_month_days = (end.month - start.month) * 30
    start_day = start.day
    end_day = end.day
    
    if start_day == 31: start_day = 30
    if end_day == 31 and (start_day == 31 or start_day == 30): end_day = 30
    
    thirty_days = total_year_days + total_month_days - start_day + end_day
    
    return thirty_days

def get_actual_days(start: dt.date, end: dt.date):
    return (end - start).days

def act_360(start: dt.date, end: dt.date):
    return get_actual_days(start, end) / 360

def act_365(start: dt.date, end: dt.date):
    return get_actual_days(start, end) / 365

def thirty_360(start: dt.date, end: dt.date):
    return get_thirty_days(start, end, 360) / 360

def thirty_365(start: dt.date, end: dt.date):
    return get_thirty_days(start, end, 365) / 365

def bus_252(start: dt.date, end: dt.date, hols: list[dt.date]):
    return len(pd.bdate_range(start, end, freq="C", holidays=hols, inclusive="left")) / 252

def yearfrac(start: dt.date, end: dt.date, daycount: Daycount, currency: str = None) -> None | float:
    hols = None
    
    if currency is not None:
        hols = get_holidays(currency, years = tuple(range(start.year, end.year + 1)))
        
    yearfrac_fn = DAYCOUNT_FN_MAP.get(daycount)
    
    if yearfrac_fn is None:
        raise KeyError(f"Error: Invalid / Unimplemented daycount convention '{daycount}'. Valid daycount conventions are: {list(Daycount)}")
    
    if daycount == Daycount.BUS_252:
        return yearfrac_fn(start, end, hols)
    
    return yearfrac_fn(start, end)

DAYCOUNT_FN_MAP = {
    Daycount.ACT_360: act_360,
    Daycount.ACT_365: act_365,
    Daycount.THIRTY_360: thirty_360,
    Daycount.THIRTY_365: thirty_365,
    Daycount.BUS_252: bus_252
}