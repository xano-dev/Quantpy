from qp.utils.maps.currency.currencies import Currency
from qp.time.date.holiday_helper import get_holidays

import datetime as dt
import numpy as np


def compute_historic_ois_fixing_dates(
    start_date: dt.date,
    valuation_date: dt.date,
    first_period_end_date: dt.date,
    lookback: int,
    currency: Currency,
):

    days = []
    future_days = []
    step = start_date

    hols = get_holidays(
        currency, (start_date.year - 1, start_date.year, start_date.year + 1)
    )

    while step <= first_period_end_date:
        days.append(step)
        if step >= np.busday_offset(
            valuation_date, lookback, holidays=[hol.isoformat() for hol in hols]
        ):
            future_days.append(step)
        np_lagged_date = np.busday_offset(
            step.isoformat(), 1, holidays=[hol.isoformat() for hol in hols]
        )
        timestamp = (
            (np_lagged_date - np.datetime64("1970-01-01T00:00:00"))
            / np.timedelta64(1, "s")
        ).item()
        step = dt.datetime.fromtimestamp(timestamp).date()

    days = np.array(days, dtype="datetime64[D]")
    future_days = np.array(future_days, dtype="datetime64[D]")

    return np.sort(days), np.sort(future_days)
