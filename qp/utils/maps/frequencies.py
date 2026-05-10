from dateutil.relativedelta import relativedelta

FREQUENCY_MAP = {
    "monthly": relativedelta(months=1),
    "quarterly": relativedelta(months=3),
    "semiannual": relativedelta(months=6),
    "annual": relativedelta(months=12),
}
