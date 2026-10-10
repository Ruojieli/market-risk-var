"""Black-Scholes pricing and Greeks for a European call.

Vectorized: S and sigma can be numpy arrays, which lets the VaR models revalue
the option under thousands of scenarios at once.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def _d1_d2(S, K, T, r, sigma):
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return d1, d1 - sigma * np.sqrt(T)


def call_price(S, K, T, r, sigma):
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def call_delta(S, K, T, r, sigma):
    """dPrice/dS."""
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return norm.cdf(d1)


def call_gamma(S, K, T, r, sigma):
    """d2Price/dS2."""
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))


def call_vega(S, K, T, r, sigma):
    """dPrice/dsigma, per 1.00 (100 vol points) change in volatility."""
    d1, _ = _d1_d2(S, K, T, r, sigma)
    return S * norm.pdf(d1) * np.sqrt(T)


def call_theta(S, K, T, r, sigma):
    """dPrice/dt per year (negative: value lost as time passes)."""
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    return (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
            - r * K * np.exp(-r * T) * norm.cdf(d2))
