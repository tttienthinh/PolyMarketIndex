# CLAUDE.md

## Project

Exploration of Polymarket "SPX Up or Down" daily contracts as a directional signal
for the S&P 500. Pure research — no live trading, no broker integration.

Stack: Python, Jupyter notebooks, yfinance, Polymarket CLOB API.

---

## Structure

```
data/               # Raw: Polymarket JSON snapshots, SPX CSV from yfinance
data_processed/     # Merged, cleaned Parquet files ready for analysis
01-data_collection.ipynb
02-eda.ipynb
03-signal_engineering.ipynb
04-backtesting.ipynb
05-position_sizing.ipynb
```

Notebooks are the primary working environment. No `src/` module for now.

---

## Key Concepts

**Polymarket contract** — Binary market resolving "Up" if SPX official close
(WSJ, rounded to nearest cent) is higher than the previous trading day's close.
Contract slug format: `spx-up-or-down-on-april-9-2026`

**Signal** — `P(Up)` sampled at some fixed window before NYSE close (4 PM ET).
Snapshot timing is an open research variable.

**Position** — A scalar in `[-1, +1]`. `+1` = full long, `-1` = full short, `0` = cash.

---

## Sizing Strategies

```python
# 1. Binary threshold
def threshold(p_up, theta=0.60):
    if p_up > theta: return 1.0
    if p_up < 1 - theta: return -1.0
    return 0.0

# 2. Proportional
def proportional(p_up):
    return 2 * p_up - 1

# 3. Kelly (symmetric payoff)
def kelly(p_up, fraction=1.0):
    return fraction * (2 * p_up - 1)

# 4. Long / Cash blend (no short)
def long_cash(p_up, theta=0.55):
    if p_up > theta:
        return 2 * (p_up - 0.5)
    return 0.0
```

---

## Execution Assumption (backtesting)

- Signal generated from Polymarket snapshot at time T (before close)
- Execution price = SPX close of the **same day**
- Daily PnL = `signal × SPX_simple_return_next_day`
- No transaction costs in baseline

---

## Open Questions

- Which snapshot time gives the cleanest signal? (T−15m, T−30m, T−60m, intraday drift)
- How far back does Polymarket historical data go?
- Is P(Up) well-calibrated vs realised outcomes? (Brier score, reliability diagram)
- Which sizing rule maximises Sharpe / minimises drawdown?
- What instrument to eventually trade? (SPY, ES/MES futures, 0DTE options)

---

## Conventions

- Timestamps stored in UTC, displayed in ET
- SPX returns are simple (not log)
- Data files saved as Parquet in `data_processed/`, raw JSON/CSV in `data/`
- Random seed: `42`
