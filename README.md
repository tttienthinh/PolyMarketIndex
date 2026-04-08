# PolyMarketIndex

Exploration project investigating whether Polymarket's daily "SPX Up or Down"
prediction market probabilities can drive a simple directional strategy on the S&P 500.

---

## Hypothesis

Polymarket's binary contracts on SPX direction aggregate crowd probability estimates
for whether the index closes higher or lower than the previous day. This project
explores whether those probabilities — sampled before the NYSE close — contain
exploitable signal, and how to best translate them into position sizing rules.

---

## Project Structure

```
polymarket-spx/
├── data/               # Raw data: Polymarket API snapshots, SPX OHLCV from yfinance
├── data_processed/     # Cleaned and merged feature tables
├── 01-data_collection.ipynb
├── 02-eda.ipynb
├── 03-signal_engineering.ipynb
├── 04-backtesting.ipynb
├── 05-position_sizing.ipynb
├── README.md
└── CLAUDE.md
```

---

## Data Sources

| Source | What |
|---|---|
| Polymarket CLOB API | "SPX Up or Down" daily contract implied probabilities |
| yfinance (`^GSPC`) | SPX daily OHLCV |
| WSJ Market Data | Ground truth for Polymarket resolution (closes rounded to nearest cent) |

---

## Strategies to Explore

- **Binary threshold** — Long/Short 100% when `P(Up)` exceeds a threshold θ
- **Proportional** — Position size = `2 * P(Up) - 1`
- **Kelly** — Fraction of Kelly bet under symmetric payoff assumption
- **Long / Cash blend** — Long a proportion, rest in cash, scaled by confidence above 50%

---

## Status

- [ ] Data collection
- [ ] EDA & calibration
- [ ] Signal engineering
- [ ] Backtesting
- [ ] Position sizing experiments
