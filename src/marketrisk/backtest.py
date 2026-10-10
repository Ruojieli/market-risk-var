"""VaR backtesting: compare each day's VaR with the next day's realized P&L.

Realized P&L here is hypothetical P&L: the change in value of the same book over
one day, with no new trades, which is the comparison Basel backtesting uses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2

from .portfolio import TRADING_DAYS, Portfolio
from .var_models import factor_returns, historical_var


def run_backtest(port: Portfolio, prices: pd.DataFrame, window: int = 250,
                 alpha: float = 0.99, test_days: int = 500) -> pd.DataFrame:
    """Rolling historical-simulation VaR backtest over the last `test_days` days."""
    rets = factor_returns(prices)
    dates = prices.index
    rows = []
    for i in range(len(dates) - test_days - 1, len(dates) - 1):
        t, t_next = dates[i], dates[i + 1]
        history = rets.loc[:t].iloc[-window:]          # information available at t
        levels_t = prices.loc[t]
        strike = port.strike_for(levels_t["SPY"])       # book re-struck each day
        T = port.call_maturity
        var = historical_var(port, levels_t, history, strike, T, alpha)["VaR"]
        pnl = float(port.value(prices.loc[t_next], strike, T - 1 / TRADING_DAYS)
                    - port.value(levels_t, strike, T))
        rows.append({"date": t_next, "pnl": pnl, "VaR": var, "exception": pnl < -var})
    return pd.DataFrame(rows).set_index("date")


def kupiec_pof(n: int, x: int, alpha: float = 0.99) -> dict:
    """Kupiec proportion-of-failures test.

    H0: the true exception rate equals 1 - alpha. A small p-value means the number
    of exceptions is inconsistent with the stated confidence level.
    """
    p = 1 - alpha
    ll_null = (n - x) * np.log(1 - p) + x * np.log(p)
    phat = x / n
    if x == 0:
        ll_alt = 0.0
    elif x == n:
        ll_alt = 0.0
    else:
        ll_alt = (n - x) * np.log(1 - phat) + x * np.log(phat)
    lr = -2 * (ll_null - ll_alt)
    return {"n": n, "exceptions": x, "expected": n * p, "LR": float(lr),
            "p_value": float(1 - chi2.cdf(lr, df=1))}


def traffic_light(exceptions_last_250: int) -> str:
    """Basel backtesting zone for 99% VaR over 250 days."""
    if exceptions_last_250 <= 4:
        return "GREEN"
    if exceptions_last_250 <= 9:
        return "YELLOW"
    return "RED"
