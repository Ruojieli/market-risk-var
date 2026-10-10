"""Assemble a daily market risk report (Markdown) and a backtest chart."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _money(x: float) -> str:
    return f"${x:,.0f}"


def write_chart(bt: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(bt.index, bt["pnl"], width=1.0, color="#7a8796", label="Daily P&L")
    ax.plot(bt.index, -bt["VaR"], color="#1f4e79", lw=1.4, label="-VaR (99%)")
    exc = bt[bt["exception"]]
    ax.scatter(exc.index, exc["pnl"], color="#b22843", zorder=3, s=18,
               label=f"Exceptions ({len(exc)})")
    ax.axhline(0, color="#333", lw=0.6)
    ax.set_title("Historical-simulation VaR backtest")
    ax.set_ylabel("USD")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_report(asof, positions: dict, results: list[dict], es_975: float,
                 sens: dict, components: dict, bt_summary: dict, zone: str,
                 issue_counts: pd.DataFrame, lookback: int, chart_name: str) -> str:
    total = sum(positions.values())
    lines = [f"# Daily Market Risk Report — {pd.Timestamp(asof):%Y-%m-%d}", ""]

    lines += ["## 1. Positions", "", "| Position | Market value |", "|---|---:|"]
    lines += [f"| {k} | {_money(v)} |" for k, v in positions.items()]
    lines += [f"| **Total** | **{_money(total)}** |", ""]

    lines += [f"## 2. Value at Risk (1-day, 99%, {lookback}-day lookback)", "",
              "| Method | VaR | ES | VaR / book |", "|---|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['method']} | {_money(r['VaR'])} | {_money(r['ES'])} "
                     f"| {r['VaR'] / total:.2%} |")
    lines += ["", f"Expected Shortfall at 97.5% (FRTB measure), historical simulation: "
              f"**{_money(es_975)}**", ""]

    lines += ["## 3. VaR contribution by risk factor (delta-normal component VaR)", "",
              "| Factor | Component VaR | Share |", "|---|---:|---:|"]
    var_total = sum(components.values())
    lines += [f"| {k} | {_money(v)} | {v / var_total:.0%} |" for k, v in components.items()]
    lines += [""]

    lines += ["## 4. Sensitivities", "", "| Measure | Value |", "|---|---:|"]
    for k, v in sens.items():
        lines.append(f"| {k} | {v:,.4f} |" if abs(v) < 10 else f"| {k} | {_money(v)} |")
    lines += [""]

    lines += ["## 5. Backtesting (historical simulation, 99%)", "",
              f"- Observations: {bt_summary['n']}",
              f"- Exceptions: {bt_summary['exceptions']} (expected {bt_summary['expected']:.1f})",
              f"- Kupiec POF test: LR = {bt_summary['LR']:.2f}, p-value = {bt_summary['p_value']:.3f}",
              f"- Basel traffic light (last 250 days): **{zone}**", "",
              f"![Backtest]({chart_name})", ""]

    lines += ["## 6. Data quality", ""]
    if issue_counts.empty:
        lines.append("No issues found.")
    else:
        lines += ["| Check | Asset | Count |", "|---|---|---:|"]
        lines += [f"| {r.check} | {r.asset} | {r.count} |" for r in issue_counts.itertuples()]
    lines += ["", "Outlier returns are flagged for review and kept in the data; "
              "missing values on the equity calendar are forward-filled for at most one day."]
    return "\n".join(lines) + "\n"
