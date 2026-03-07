import datetime as dt
import calendar  
        
def days_between(date: dt.date, other_date: dt.date):

    delta = abs(date - other_date)
    return delta.days

def days_between_30(date: dt.date, other_date: dt.date):

    delta = abs(date.year - other_date.year) * 360 + abs(date.month - other_date.month) * 30 + abs(date.day - other_date.day)
    return delta.days    

def year_fraction_act360(date: dt.date, other_date: dt.date):
    
    days = days_between(date, other_date)
    return days / 360.0

def year_fraction_act365(date: dt.date, other_date: dt.date):

    days = days_between(date, other_date)
    return days / 365.0

def year_fraction_30360(date: dt.date, other_date: dt.date):
    
    days = days_between_30(date, other_date)
    return days / 360.0

def year_fraction_30365(date: dt.date, other_date: dt.date):
    
    days = days_between_30(date, other_date)
    return days / 365.0

def year_fraction_actact(date: dt.date, other_date: dt.date):
    
    num_years_exclusive = abs(date.year - other_date.year) - 1
    
    date_leap = calendar.isleap(date.year)
    other_leap = calendar.isleap(other_date.year)
    
    date_days_passed = (date - dt.date(date.year, 1, 1)).days
    other_days_passed = (other_date - dt.date(date.year, 1, 1)).days
    
    if date < other_date:
        if date_leap:
            date_days_remaining = 366 - date_days_passed
            date_frac = date_days_remaining / 366
        else:
            date_days_remaining = 365 - date_days_passed
            date_frac = date_days_remaining / 365
        
        if other_leap:
            other_frac = other_days_passed / 366
        else:
            other_frac = other_days_passed / 365
        
    else:
        if other_leap:
            other_days_remaining = 366 - other_days_passed
            other_frac = other_days_remaining / 366
        else:
            other_days_remaining = 365 - other_days_passed
            other_frac = other_days_remaining / 365
        
        if date_leap:
            date_frac = date_days_passed / 366
        else:
            date_frac = date_days_passed / 365
    
    return num_years_exclusive + date_frac + other_frac 