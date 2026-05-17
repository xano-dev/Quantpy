"""One-off script to seed fx_curves/fx_curves.json with real spot rates and
synthetic forward curves constructed via CIRP.

Run from the repo root:
    python qp/data/seed_fx_curves.py [YYYY-MM-DD]

The valuation date defaults to today if not provided.

Before reseeding for a significantly different date, update BENCHMARK_RATES from:
    https://tradingeconomics.com/country-list/interest-rate

Limitations:
- Forward rates are constructed from textbook CIRP using flat central bank policy
  rates at all tenors. In practice, both r_foreign and r_usd should vary by tenor
  (i.e. be sourced from full zero curves), and FX forward rates deviate from CIRP
  due to the cross-currency basis (typically -20 to -50bps for EUR/JPY/CHF vs USD),
  which reflects structural USD funding demand and post-GFC regulatory constraints.
  A production system would source forward rates directly from market quotes
  (Bloomberg/Reuters), which embed both the term structure and basis implicitly.
"""

import json
import sys
import datetime as dt
import math
import yfinance as yf

OUTPUT_PATH = "qp/data/fx_curves/fx_curves.json"

CURRENCIES = [
    "EUR",
    "GBP",
    "JPY",
    "CHF",
    "AUD",
    "CAD",
    "NZD",
    "NOK",
    "SEK",
    "HKD",
    "SGD",
]

# Central bank policy rates (annualised decimals) as of 2026-05-17.
# Source: https://tradingeconomics.com/country-list/interest-rate
BENCHMARK_RATES: dict[str, float] = {
    "USD": 0.0356,  # SOFR — Federal Reserve
    "EUR": 0.0200,  # ECB deposit facility rate
    "GBP": 0.0375,  # Bank of England
    "AUD": 0.0435,  # Reserve Bank of Australia
    "JPY": 0.0075,  # Bank of Japan
    "CHF": 0.0000,  # Swiss National Bank
    "CAD": 0.0225,  # Bank of Canada
    "NZD": 0.0225,  # Reserve Bank of New Zealand
    "NOK": 0.0425,  # Norges Bank
    "SEK": 0.0175,  # Riksbank
    "HKD": 0.0400,  # Hong Kong Monetary Authority
    "SGD": 0.0127,  # Monetary Authority of Singapore (SORA)
}

TENOR_YEARFRACS = [0.0, 1 / 12, 3 / 12, 6 / 12, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]


def fetch_spot(ccy: str, valuation_date: dt.date) -> float:
    ticker = f"{ccy}USD=X"
    start = valuation_date - dt.timedelta(days=7)
    data = yf.download(
        ticker,
        start=start,
        end=valuation_date + dt.timedelta(days=1),
        auto_adjust=True,
        progress=False,
    )
    return float(data["Close"].squeeze().dropna().iloc[-1])


def forward_rate(spot: float, tau: float, r_foreign: float, r_usd: float) -> float:
    """CIRP without cross-currency basis: F = S * exp((r_foreign - r_usd) * tau)."""
    if tau == 0.0:
        return spot
    return spot * math.exp((r_foreign - r_usd) * tau)


def build_curve(ccy: str, valuation_date: dt.date) -> dict:
    spot = fetch_spot(ccy, valuation_date)
    r_ccy = BENCHMARK_RATES[ccy]
    r_usd = BENCHMARK_RATES["USD"]

    tenor_dates = []
    fx_rates = []

    for tau in TENOR_YEARFRACS:
        days = int(round(tau * 365))
        tenor_date = valuation_date + dt.timedelta(days=days)
        tenor_dates.append(tenor_date.isoformat())
        fx_rates.append(round(forward_rate(spot, tau, r_ccy, r_usd), 6))

    return {
        "currency_1": ccy,
        "currency_2": "USD",
        "tenors": tenor_dates,
        "fx_rates": fx_rates,
        "daycount": "ACT/360",
    }


def main() -> None:
    valuation_date = (
        dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    )
    print(f"Valuation date: {valuation_date}")

    print("\nFetching spot FX rates and building curves...")
    curves = {}
    for ccy in CURRENCIES:
        print(f"  {ccy}USD...")
        curves[f"{ccy}USD"] = build_curve(ccy, valuation_date)

    try:
        with open(OUTPUT_PATH) as f:
            database = json.load(f)
    except FileNotFoundError:
        database = {}

    database[valuation_date.isoformat()] = curves

    with open(OUTPUT_PATH, "w") as f:
        json.dump(database, f, indent=2)

    print(f"\nWritten to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
