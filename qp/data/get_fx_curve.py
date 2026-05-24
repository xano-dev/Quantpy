from qp.utils.maps.currency.currencies import Currency
import json
import datetime as dt
from qp.time.date.daycount import Daycount

FX_CURVES_PATH = r"qp\data\fx_curves\fx_curves.json"


def get_fx_curve(currency: Currency, valuation_date: dt.date):
    with open(FX_CURVES_PATH) as f:
        data = json.load(f)

    val_date_str: str = dt.datetime.strftime(valuation_date, format="%Y-%m-%d")

    try:
        fx_rates: list[float] = data[val_date_str][f"{currency}USD"]["fx_rates"]
        tenors: list[dt.date] = [
            dt.datetime.strptime(date_str, "%Y-%m-%d").date()
            for date_str in data[val_date_str][f"{currency}USD"]["tenors"]
        ]
        daycount: Daycount = Daycount(data[val_date_str][f"{currency}USD"]["daycount"])
    except KeyError:
        raise KeyError(
            f"Currency {currency} not in database - please add relevant data to seed_fx_curves.py"
        )

    return fx_rates, tenors, daycount
