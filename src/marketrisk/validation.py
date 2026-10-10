"""Data quality checks run before any risk number is produced.

Each check records issues instead of silently fixing them, so the report can
show what was found and what was done about it (the "break analysis").
"""
from __future__ import annotations

import pandas as pd


def validate_prices(prices: pd.DataFrame, master: str = "SPY", max_ffill: int = 1,
                    stale_days: int = 3, outlier_z: float = 6.0,
                    window: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean raw closes and return (clean_prices, issues).

    Checks:
      1. Non-positive prices.
      2. Calendar alignment: the master asset's trading days define the calendar;
         other factors missing on those days are forward-filled up to `max_ffill`
         days (e.g. an FX or index holiday), and days still incomplete are dropped.
      3. Stale prices: the same close repeated for `stale_days` or more days.
      4. Outlier returns: |return| above `outlier_z` times the trailing
         `window`-day volatility. Flagged for review, not removed.
    """
    issues: list[dict] = []

    def log(date, asset, check, detail):
        issues.append({"date": date, "asset": asset, "check": check, "detail": detail})

    # 1. Non-positive prices
    for col in prices.columns:
        for date, val in prices[col][prices[col] <= 0].items():
            log(date, col, "non-positive price", f"{val}")

    # 2. Calendar alignment on the master asset's trading days
    calendar = prices[master].dropna().index
    aligned = prices.loc[calendar]
    for col in aligned.columns:
        for date in aligned.index[aligned[col].isna()]:
            log(date, col, "missing on trading day", "forward-filled if within limit")
    filled = aligned.ffill(limit=max_ffill)
    incomplete = filled.index[filled.isna().any(axis=1)]
    for date in incomplete:
        log(date, "ALL", "incomplete day dropped", "gap longer than fill limit")
    clean = filled.drop(index=incomplete)

    # 3. Stale prices: count consecutive repeats of the same close
    for col in clean.columns:
        same = clean[col].diff().eq(0)
        run_len = same.groupby((~same).cumsum()).cumsum()
        for date in run_len.index[run_len == stale_days - 1]:
            log(date, col, "stale price", f"unchanged for {stale_days} days")

    # 4. Outlier returns relative to trailing volatility
    rets = clean.pct_change()
    vol = rets.rolling(window).std().shift(1)
    z = rets / vol
    for col in clean.columns:
        for date, zval in z[col][z[col].abs() > outlier_z].items():
            log(date, col, "outlier return",
                f"return {rets.at[date, col]:+.2%}, {zval:+.1f}x trailing vol")

    issues_df = pd.DataFrame(issues, columns=["date", "asset", "check", "detail"])
    return clean, issues_df


def summarize_issues(issues: pd.DataFrame) -> pd.DataFrame:
    """Count issues by check and asset for the report."""
    if issues.empty:
        return pd.DataFrame(columns=["check", "asset", "count"])
    return (issues.groupby(["check", "asset"]).size()
            .rename("count").reset_index().sort_values(["check", "asset"]))
