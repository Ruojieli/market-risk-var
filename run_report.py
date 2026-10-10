"""Produce the daily market risk report.

Usage:
    python run_report.py              # use cached prices
    python run_report.py --refresh    # download fresh prices first
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from marketrisk.backtest import kupiec_pof, run_backtest, traffic_light  # noqa: E402
from marketrisk.data import load_prices  # noqa: E402
from marketrisk.portfolio import Portfolio  # noqa: E402
from marketrisk.report import build_report, write_chart  # noqa: E402
from marketrisk.validation import summarize_issues, validate_prices  # noqa: E402
from marketrisk.var_models import (factor_returns, historical_var,  # noqa: E402
                                   monte_carlo_var, parametric_var)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--refresh", action="store_true", help="download fresh prices")
    ap.add_argument("--lookback", type=int, default=500, help="days of history for VaR")
    ap.add_argument("--alpha", type=float, default=0.99, help="VaR confidence level")
    args = ap.parse_args()

    raw = load_prices(refresh=args.refresh)
    prices, issues = validate_prices(raw)

    port = Portfolio()
    asof = prices.index[-1]
    levels = prices.loc[asof]
    strike, T = port.strike_for(levels["SPY"]), port.call_maturity
    rets = factor_returns(prices).iloc[-args.lookback:]

    hs = historical_var(port, levels, rets, strike, T, args.alpha)
    pm = parametric_var(port, levels, rets, strike, T, args.alpha)
    mc = monte_carlo_var(port, levels, rets, strike, T, args.alpha)
    es_975 = historical_var(port, levels, rets, strike, T, 0.975)["ES"]

    bt = run_backtest(port, prices, window=250, alpha=args.alpha, test_days=500)
    summary = kupiec_pof(len(bt), int(bt["exception"].sum()), args.alpha)
    zone = traffic_light(int(bt["exception"].iloc[-250:].sum()))

    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    chart = out / "backtest.png"
    write_chart(bt, chart)
    report = build_report(asof, port.positions(levels, strike, T), [hs, pm, mc], es_975,
                          port.sensitivities(levels, strike, T), pm["components"],
                          summary, zone, summarize_issues(issues), args.lookback, chart.name)
    path = out / f"risk_report_{asof:%Y-%m-%d}.md"
    path.write_text(report)

    print(f"As of {asof:%Y-%m-%d}")
    for r in (hs, pm, mc):
        print(f"  {r['method']:<32} VaR {r['VaR']:>12,.0f}   ES {r['ES']:>12,.0f}")
    print(f"  ES 97.5% (historical)            {es_975:>12,.0f}")
    print(f"  Backtest: {summary['exceptions']} exceptions in {summary['n']} days "
          f"(expected {summary['expected']:.1f}), Kupiec p = {summary['p_value']:.3f}, zone {zone}")
    print(f"  Data issues logged: {len(issues)}")
    print(f"Report written to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
