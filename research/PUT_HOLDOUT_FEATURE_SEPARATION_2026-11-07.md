# PUT holdout feature-separation diagnostic — 2026-11-07

## Purpose

A narrow follow-up on the historical 376-trade M5 PUT holdout log. Question: can common pre-entry market-state features separate winning from losing trades, and therefore explain the apparent June–July edge decay?

This is an exploratory diagnostic on an already-inspected holdout. It is not a fresh validation, strategy search, or permission to deploy a filter.

## Inputs and alignment

- OHLC source: `eurusd_research_clean.csv`, SHA-256 `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- 486,488 M1 rows, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- UTC-aligned complete M5 aggregation: 97,227 bars, 68 continuous segments.
- Trade outcomes: `hydra_m5_put_holdout_trades.csv`, 376 entries.
- Trade timestamps identify the final M1 minute of the entry M5 candle. For every trade, features were taken from the immediately preceding, fully closed M5 signal candle. No entry-candle or future data were used for features.
- The ten draws were retained in descriptive data but excluded from decisive win-rate comparisons.
- Feature estimates use pandas EWM/Wilder-style smoothing. They are diagnostic approximations, not a bit-for-bit reproduction of the unavailable original screening implementation.

## Overall reference

- 376 logged trades: 197 wins, 169 losses, 10 draws.
- Decisive win rate: 53.825%.
- Net at 92% payout: +12.24 units.
- Wilson 95% interval for decisive WR: approximately 48.70%–58.87%.
- This is not statistically persuasive evidence that the true win probability exceeds the 52.0833% break-even threshold.

## Pre-entry feature separation

The 376 trades were split into four equal-sized groups by each feature. Win rates below exclude draws.

| Feature on prior closed M5 candle | Q1 WR | Q2 WR | Q3 WR | Q4 WR | Win/loss rank test p |
|---|---:|---:|---:|---:|---:|
| RSI(14) | 48.94% | 51.06% | 53.19% | 56.38% | 0.399 |
| ADX(14) | 44.68% | 52.13% | 56.38% | 56.38% | 0.160 |
| ATR(14) / close, bps | 51.06% | 54.26% | 47.87% | 56.38% | 0.347 |
| 3-bar return | 52.13% | 51.06% | 59.57% | 46.81% | 0.977 |
| EMA20–EMA50 / ATR | 55.32% | 46.81% | 51.06% | 56.38% | 0.822 |
| Bollinger z-score(20) | 50.00% | 51.06% | 53.19% | 55.32% | 0.314 |

All six univariate rank tests are non-significant. The visually higher Q4 rates for RSI/ADX are modest, overlap substantially in uncertainty, and were examined post hoc. The ADX Q1→Q4 gradient is not enough to justify an ADX threshold; selecting it now would be holdout fitting.

The 3-bar return has essentially no monotonic relationship with outcome (Spearman rho approximately -0.002). That is consistent with the earlier finding that simple recent upward momentum did not explain the historical edge decay.

## Interpretation

1. No tested single feature cleanly separates wins from losses in this holdout.
2. ADX shows the strongest weak univariate hint (p≈0.160), but it is far from confirmatory and is vulnerable to multiple-testing selection.
3. RSI, volatility, EMA trend separation, Bollinger position, and short momentum do not provide a defensible post-hoc filter.
4. This does not disprove the original PUT signal. It says these common state variables, measured on the prior closed M5 candle, do not explain its trade outcomes convincingly in this sample.
5. The earlier June–July versus August–October split remains suggestive, not established: the difference may reflect chance, a changing signal, quote/data conditions, or unmeasured context.

## Decision

- Do not add an ADX/RSI/time-of-day filter to the old PUT setup.
- Do not alter production/Desktop math core.
- Keep CALL and PUT research separate.
- The original signal-generation code and full train trade timestamp log are still missing from the recovered repository artifacts. Exact parity cannot be claimed.
- Next useful experiment: obtain the original train signal timestamps or source implementation; otherwise design new PUT hypotheses on a chronological development window and reserve a genuinely untouched later period for confirmation. Evaluate at 92% payout with non-overlap, gap-aware execution and realistic quote timing.

