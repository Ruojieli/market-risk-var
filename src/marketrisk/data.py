"""Download and cache daily closes for the portfolio's risk factors."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Risk factor name -> Yahoo Finance ticker
TICKERS = {"SPY": "SPY", "TLT": "TLT", "EURUSD": "EURUSD=X", "VIX": "^VIX"}

CACHE = Path(__file__).resolve().parents[2] / "data" / "prices.csv"


def load_prices(start: str = "2019-01-01", end: str | None = None,
                refresh: bool = False, cache_path: Path = CACHE) -> pd.DataFrame:
    """Return raw daily closes, one column per risk factor.

    Reads the local cache when it exists so results are reproducible offline;
    pass refresh=True to download fresh data.
    """
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path, index_col=0, parse_dates=True)

    import yfinance as yf

    raw = yf.download(list(TICKERS.values()), start=start, end=end,
                      progress=False, auto_adjust=True)["Close"]
    prices = raw.rename(columns={v: k for k, v in TICKERS.items()})[list(TICKERS)]
    prices.index = pd.to_datetime(prices.index)
    if prices.index.tz is not None:
        prices.index = prices.index.tz_localize(None)
    prices.index.name = "date"

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(cache_path)
    return prices
