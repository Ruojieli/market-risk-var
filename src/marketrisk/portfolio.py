"""A small multi-asset book for a USD-based investor.

Positions
  SPY        long equity ETF shares
  TLT        long long-duration Treasury ETF shares (rates exposure)
  EUR        long euro cash, valued in USD at EURUSD (FX exposure)
  SPY calls  long 3-month calls struck 5% out of the money (non-linear exposure)

Risk factors: SPY, TLT, EURUSD, VIX. VIX/100 is used as a proxy for the calls'
implied volatility, so VIX moves create vega P&L.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import greeks

TRADING_DAYS = 252
FACTORS = ["SPY", "TLT", "EURUSD", "VIX"]


@dataclass
class Portfolio:
    spy_shares: float = 1_000
    tlt_shares: float = 2_000
    eur_notional: float = 500_000
    n_calls: float = 2_000            # 20 contracts x 100 multiplier
    call_moneyness: float = 1.05      # strike = 105% of spot when the book is struck
    call_maturity: float = 0.25       # years
    rate: float = 0.04                # flat risk-free rate (simplification)

    def strike_for(self, spot: float) -> float:
        return float(np.round(spot * self.call_moneyness))

    def value(self, levels, strike: float, T: float):
        """Mark-to-market value in USD. `levels` maps factor -> level (scalar or array)."""
        S, P, fx, vix = (np.asarray(levels[f], dtype=float) for f in FACTORS)
        call = greeks.call_price(S, strike, T, self.rate, vix / 100.0)
        return (self.spy_shares * S + self.tlt_shares * P
                + self.eur_notional * fx + self.n_calls * call)

    def positions(self, levels, strike: float, T: float) -> dict:
        """Market value of each position, for the report."""
        S, P, fx, vix = (float(levels[f]) for f in FACTORS)
        call = float(greeks.call_price(S, strike, T, self.rate, vix / 100.0))
        return {
            "SPY shares": self.spy_shares * S,
            "TLT shares": self.tlt_shares * P,
            "EUR cash": self.eur_notional * fx,
            f"SPY {strike:.0f} calls ({T * 12:.0f}M)": self.n_calls * call,
        }

    def exposures(self, levels, strike: float, T: float) -> dict:
        """Dollar P&L for a +1.00 (100%) relative move in each factor (linear approximation).

        SPY includes the calls' delta; VIX exposure is the calls' vega scaled by the
        vol level, because a relative VIX move r changes sigma by sigma * r.
        """
        S, P, fx, vix = (float(levels[f]) for f in FACTORS)
        sigma = vix / 100.0
        delta = float(greeks.call_delta(S, strike, T, self.rate, sigma))
        vega = float(greeks.call_vega(S, strike, T, self.rate, sigma))
        return {
            "SPY": (self.spy_shares + self.n_calls * delta) * S,
            "TLT": self.tlt_shares * P,
            "EURUSD": self.eur_notional * fx,
            "VIX": self.n_calls * vega * sigma,
        }

    def sensitivities(self, levels, strike: float, T: float) -> dict:
        """Greeks and risk sensitivities expressed in the units desks report."""
        S, _, _, vix = (float(levels[f]) for f in FACTORS)
        sigma = vix / 100.0
        args = (S, strike, T, self.rate, sigma)
        delta = float(greeks.call_delta(*args))
        gamma = float(greeks.call_gamma(*args))
        vega = float(greeks.call_vega(*args))
        theta = float(greeks.call_theta(*args))
        exp = self.exposures(levels, strike, T)
        return {
            "Call delta (per option)": delta,
            "Equity delta: $ P&L per +1% SPY": exp["SPY"] * 0.01,
            "Gamma: change in $ delta per +1% SPY": self.n_calls * gamma * S * 0.01 * S * 0.01,
            "Vega: $ P&L per +1 vol point": self.n_calls * vega * 0.01,
            "Theta: $ P&L per day": self.n_calls * theta / TRADING_DAYS,
            "Rates proxy: $ P&L per +1% TLT": exp["TLT"] * 0.01,
            "FX: $ P&L per +1% EURUSD": exp["EURUSD"] * 0.01,
        }
