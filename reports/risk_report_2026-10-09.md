# Daily Market Risk Report — 2026-10-09

## 1. Positions

| Position | Market value |
|---|---:|
| SPY shares | $778,570 |
| TLT shares | $155,960 |
| EUR cash | $560,287 |
| SPY 817 calls (3M) | $22,761 |
| **Total** | **$1,517,578** |

## 2. Value at Risk (1-day, 99%, 500-day lookback)

| Method | VaR | ES | VaR / book |
|---|---:|---:|---:|
| Historical simulation | $22,859 | $36,258 | 1.51% |
| Parametric (delta-normal) | $25,860 | $29,627 | 1.70% |
| Monte Carlo (full revaluation) | $24,896 | $28,456 | 1.64% |

Expected Shortfall at 97.5% (FRTB measure), historical simulation: **$26,265**

## 3. VaR contribution by risk factor (delta-normal component VaR)

| Factor | Component VaR | Share |
|---|---:|---:|
| SPY | $29,119 | 113% |
| TLT | $679 | 3% |
| EURUSD | $1,529 | 6% |
| VIX | $-5,468 | -21% |

## 4. Sensitivities

| Measure | Value |
|---|---:|
| Call delta (per option) | 0.3165 |
| Equity delta: $ P&L per +1% SPY | $12,714 |
| Gamma: change in $ delta per +1% SPY | $747 |
| Vega: $ P&L per +1 vol point | $2,771 |
| Theta: $ P&L per day | $-401 |
| Rates proxy: $ P&L per +1% TLT | $1,560 |
| FX: $ P&L per +1% EURUSD | $5,603 |

## 5. Backtesting (historical simulation, 99%)

- Observations: 500
- Exceptions: 8 (expected 5.0)
- Kupiec POF test: LR = 1.54, p-value = 0.215
- Basel traffic light (last 250 days): **GREEN**

![Backtest](backtest.png)

## 6. Data quality

| Check | Asset | Count |
|---|---|---:|
| missing on trading day | EURUSD | 2 |
| outlier return | EURUSD | 1 |
| outlier return | SPY | 1 |
| outlier return | VIX | 7 |

Outlier returns are flagged for review and kept in the data; missing values on the equity calendar are forward-filled for at most one day.
