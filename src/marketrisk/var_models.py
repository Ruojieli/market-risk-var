"""Three ways to estimate 1-day Value at Risk and Expected Shortfall.

All functions report losses as positive numbers:
  VaR(alpha) = loss not exceeded with probability alpha
  ES(alpha)  = average loss on days worse than VaR(alpha)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .portfolio import FACTORS, TRADING_DAYS, Portfolio


def factor_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily simple returns of the risk factors."""
    return prices[FACTORS].pct_change().dropna()


def _tail(pnl: np.ndarray, alpha: float) -> tuple[float, float]:
    var = -np.quantile(pnl, 1 - alpha)
    es = -pnl[pnl <= -var].mean()
    return float(var), float(es)


def _full_revaluation(port: Portfolio, levels0: pd.Series, shocks: np.ndarray,
                      strike: float, T: float) -> np.ndarray:
    """P&L of the book under each scenario of relative factor shocks (rows = scenarios)."""
    shocked = {f: float(levels0[f]) * (1 + shocks[:, i]) for i, f in enumerate(FACTORS)}
    v0 = port.value(levels0, strike, T)
    v1 = port.value(shocked, strike, T - 1 / TRADING_DAYS)   # one day of time decay
    return v1 - v0


def historical_var(port: Portfolio, levels0: pd.Series, rets: pd.DataFrame,
                   strike: float, T: float, alpha: float = 0.99) -> dict:
    """Historical simulation: replay each past day's factor moves on today's book."""
    pnl = _full_revaluation(port, levels0, rets[FACTORS].to_numpy(), strike, T)
    var, es = _tail(pnl, alpha)
    return {"method": "Historical simulation", "VaR": var, "ES": es, "pnl": pnl}


def parametric_var(port: Portfolio, levels0: pd.Series, rets: pd.DataFrame,
                   strike: float, T: float, alpha: float = 0.99) -> dict:
    """Delta-normal: linear exposures and a normal distribution of factor returns.

    Fast and decomposable, but it ignores option convexity (gamma) and fat tails.
    """
    exp = port.exposures(levels0, strike, T)
    e = np.array([exp[f] for f in FACTORS])
    cov = rets[FACTORS].cov().to_numpy()
    sigma_p = float(np.sqrt(e @ cov @ e))
    z = norm.ppf(alpha)
    # Component VaR: each factor's share of total VaR; the components sum to VaR.
    components = dict(zip(FACTORS, e * (cov @ e) / sigma_p * z))
    return {"method": "Parametric (delta-normal)", "VaR": z * sigma_p,
            "ES": sigma_p * norm.pdf(z) / (1 - alpha), "components": components}


def monte_carlo_var(port: Portfolio, levels0: pd.Series, rets: pd.DataFrame,
                    strike: float, T: float, alpha: float = 0.99,
                    n_sims: int = 20_000, seed: int = 42) -> dict:
    """Monte Carlo: simulate correlated normal factor moves, then fully revalue the book."""
    rng = np.random.default_rng(seed)
    cov = rets[FACTORS].cov().to_numpy()
    # Correlate independent standard normals with the Cholesky factor: cov = L L'
    L = np.linalg.cholesky(cov)
    z = rng.standard_normal((n_sims, len(FACTORS)))
    shocks = np.einsum("nk,jk->nj", z, L)   # same as z @ L.T
    pnl = _full_revaluation(port, levels0, shocks, strike, T)
    var, es = _tail(pnl, alpha)
    return {"method": "Monte Carlo (full revaluation)", "VaR": var, "ES": es, "pnl": pnl}
