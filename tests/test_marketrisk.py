"""Sanity checks that each building block matches a known answer."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marketrisk import greeks  # noqa: E402
from marketrisk.backtest import kupiec_pof, traffic_light  # noqa: E402
from marketrisk.portfolio import FACTORS, Portfolio  # noqa: E402
from marketrisk.validation import validate_prices  # noqa: E402
from marketrisk.var_models import (historical_var, monte_carlo_var,  # noqa: E402
                                   parametric_var)

LEVELS = pd.Series({"SPY": 500.0, "TLT": 90.0, "EURUSD": 1.10, "VIX": 20.0})


def equity_only():
    """A book holding only SPY shares, so every method should agree with theory."""
    return Portfolio(spy_shares=1_000, tlt_shares=0, eur_notional=0, n_calls=0)


def normal_returns(n=200_000, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    data = {f: rng.normal(0, vol if f == "SPY" else 0.005, n) for f in FACTORS}
    return pd.DataFrame(data)


def test_put_call_parity_and_delta_bounds():
    S, K, T, r, s = 100.0, 105.0, 0.25, 0.04, 0.2
    call = greeks.call_price(S, K, T, r, s)
    put = call - S + K * np.exp(-r * T)
    assert put > 0
    assert 0 < greeks.call_delta(S, K, T, r, s) < 1


def test_delta_matches_finite_difference():
    S, K, T, r, s, h = 100.0, 105.0, 0.25, 0.04, 0.2, 1e-4
    fd = (greeks.call_price(S + h, K, T, r, s) - greeks.call_price(S - h, K, T, r, s)) / (2 * h)
    assert greeks.call_delta(S, K, T, r, s) == pytest.approx(fd, rel=1e-6)


def test_parametric_var_equals_closed_form():
    port, rets = equity_only(), normal_returns()
    res = parametric_var(port, LEVELS, rets, strike=525, T=0.25, alpha=0.99)
    expected = norm.ppf(0.99) * 1_000 * 500 * rets["SPY"].std()
    assert res["VaR"] == pytest.approx(expected, rel=1e-9)
    assert sum(res["components"].values()) == pytest.approx(res["VaR"], rel=1e-9)


def test_three_methods_agree_for_linear_normal_book():
    port, rets = equity_only(), normal_returns()
    hs = historical_var(port, LEVELS, rets, 525, 0.25)["VaR"]
    pm = parametric_var(port, LEVELS, rets, 525, 0.25)["VaR"]
    mc = monte_carlo_var(port, LEVELS, rets, 525, 0.25, n_sims=200_000)["VaR"]
    assert hs == pytest.approx(pm, rel=0.02)
    assert mc == pytest.approx(pm, rel=0.02)


def test_es_exceeds_var():
    res = historical_var(equity_only(), LEVELS, normal_returns(), 525, 0.25)
    assert res["ES"] > res["VaR"]


def test_kupiec_accepts_expected_rate_and_rejects_too_many():
    assert kupiec_pof(250, 2, 0.99)["p_value"] > 0.05
    assert kupiec_pof(250, 12, 0.99)["p_value"] < 0.01


def test_traffic_light_zones():
    assert traffic_light(4) == "GREEN"
    assert traffic_light(5) == "YELLOW"
    assert traffic_light(10) == "RED"


def test_validation_fills_one_day_gap_and_flags_stale_price():
    idx = pd.bdate_range("2024-01-01", periods=10)
    prices = pd.DataFrame({"SPY": np.arange(100, 110, dtype=float),
                           "TLT": [90.0] * 10,                     # stale for 10 days
                           "EURUSD": [1.1] * 4 + [np.nan] + [1.1 + i / 100 for i in range(5)],
                           "VIX": np.linspace(15, 20, 10)}, index=idx)
    clean, issues = validate_prices(prices, stale_days=3)
    assert clean["EURUSD"].isna().sum() == 0
    assert ((issues["check"] == "stale price") & (issues["asset"] == "TLT")).any()
    assert ((issues["check"] == "missing on trading day") & (issues["asset"] == "EURUSD")).any()
