# CALL / PUT win-pattern research — 2026-11-08

## Status and scope

This is a synthesis of the reproducible M5 BB(20, 2) + Williams %R(14) + ADX(14) diagnostic already recorded in `CALL_VS_PUT_DIAGNOSTIC_2026-11-07.md`. It is **not a new backtest run** and does not claim fresh observations. The source diagnostic used 30,048 EUR/USD M1 rows from 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC, complete UTC-aligned M5 bars, one-candle horizon, next M5 open entry, close settlement, shared non-overlap scheduling, and 92% payout.

Purpose: identify whether CALL and PUT outcomes show a stable, direction-specific pre-signal context pattern, while separating signal context from the underlying market's directional drift.

## 1. Frozen aggregate outcome

| Direction | Trades | Wins | Losses | Draws | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| CALL | 86 | 52 | 31 | 3 | 62.65% | +16.84 |
| PUT | 59 | 27 | 29 | 3 | 48.21% | -4.16 |

Direction comparison: Fisher exact p=0.1164. Wilson 95% intervals: CALL 51.90–72.28%; PUT 35.67–60.99%. The directional difference is not statistically established.

## 2. Market-context pattern is larger than the apparent strategy-direction gap

The sample's unconditional next-candle direction was 55.89% UP and 44.11% DOWN (flat candles excluded). The strategy-side context baselines, conditioned coarsely on DMI x prior 3-bar M5 momentum, were:

| Direction | Strategy WR | Same-context background WR | Incremental lift |
|---|---:|---:|---:|
| CALL | 62.65% | 59.20% | +3.45 pp |
| PUT | 48.21% | 46.82% | +1.39 pp |

The raw CALL–PUT gap is 14.44 pp, while the background UP-vs-DOWN rates already differ by about 12.38 pp. Most of the raw gap is therefore consistent with the different market contexts in which these mean-reversion triggers occur. The remaining lifts are small and descriptive; the background is overlapping and is not a matched causal control.

## 3. Chronological split changes the interpretation

| Period | Direction | Strategy WR | Context baseline | Lift |
|---|---|---:|---:|---:|
| Train | CALL | 56.86% | 58.85% | -1.98 pp |
| Train | PUT | 47.50% | 46.47% | +1.03 pp |
| Holdout | CALL | 71.88% | 60.40% | +11.47 pp |
| Holdout | PUT | 50.00% | 47.53% | +2.47 pp |

CALL's incremental lift is negative in train and positive in holdout. This is not evidence of a stable CALL-specific winning pattern; it may be a regime change or sampling noise. Holdout counts are only 32 CALL and 16 PUT decisive trades.

## 4. Direction-specific context observations

At ADX >=15, prior 3-bar M5 momentum splits were:

| Context | CALL | PUT |
|---|---:|---:|
| Momentum DOWN, full sample | 63.93% (39/61 decisive) | 43.48% (10/23) |
| Momentum UP, full sample | 59.09% (13/22) | 53.12% (17/32) |
| Momentum DOWN, holdout | 68.00% (17/25) | 28.57% (2/7) |
| Momentum UP, holdout | 85.71% (6/7) | 75.00% (6/8) |

These are small, post-hoc cells. The very high holdout rates in tiny cells are especially unstable. They must not be converted into filters.

DMI also reveals a structural imbalance: 82/86 CALL trades occurred with -DI > +DI, while 55/59 PUT trades occurred with +DI > -DI. Because the mean-reversion triggers naturally fire in opposite directional pressure states, a same-DMI-cell CALL-vs-PUT comparison has poor overlap and can be misleading.

## 5. What can and cannot be said about winning patterns

**Supported by the current diagnostic:**
- CALL and PUT signals are emitted in markedly different market states.
- A coarse DMI x momentum context baseline explains much of the unadjusted CALL-vs-PUT win-rate difference.
- The residual lift is modest across the full sample and not stable across the chronological split.
- No context split presented here establishes a durable, profitable CALL or PUT edge at 92%.

**Not yet tested rigorously enough:**
- A full winner-vs-loser feature-separation analysis for both directions using the same exact frozen trade log and the exact signal-time feature vector.
- Whether interactions among candle structure, volatility expansion/contraction, trend strength, distance from bands, and momentum distinguish winners from losers after correcting for multiple comparisons.
- Whether any such relationship persists in an independent, later prospective sample.

The separate legacy PUT holdout feature-separation note found no significant single-feature separation (RSI p=0.399, ADX p=0.160, ATR/close p=0.347, 3-bar return p=0.977, EMA separation p=0.822, Bollinger z-score p=0.314). That 376-trade legacy log is a different strategy/history and must not be pooled with the October M5 BB/Williams/ADX candidate.

## 6. Next controlled experiment

1. Reconstruct the exact frozen candidate's full signal log with a row for every eligible signal, including wins, losses, and draws; store the signal candle timestamp and the feature vector available at that close.
2. Calculate features only from fully closed candles before entry: RSI, ADX, +DI/-DI, EMA separation/ATR, Bollinger z-score/width, ATR percentile, prior candle body and wick ratios, M1/M5 returns over fixed horizons, consecutive candle direction, and UTC session.
3. Analyse CALL and PUT independently. Compare winner vs loser feature distributions (effect size, rank test and confidence interval); keep draws separate. Report all tested features, not only the strongest.
4. Correct the discovery-stage p-values for multiple testing (Benjamini–Hochberg) and account for time clustering; naive independent-trade p-values are not enough.
5. Discover any simple candidate rule on chronological train only. Freeze its exact definition before looking at holdout.
6. Evaluate once on the untouched later holdout and then prospectively. Report trade count, W/L/D, decisive WR, Wilson interval, net units at 92%, ROI, profit factor, max drawdown, max losing streak, coverage and WAIT share.
7. Keep CALL and PUT separate throughout. Do not combine them to conceal a losing side. Do not modify the Desktop math core or promote a filter on the basis of this exploratory sample.

## Verdict

There is a repeatable **context difference** between CALL and PUT triggers, but no confirmed stable **winner fingerprint** yet. The strongest current lead is that the raw CALL advantage largely tracks the market context in which CALLs occur, not an established intrinsic advantage of CALL. The correct next step is a direction-separated, signal-time winner-vs-loser feature study with strict train/holdout separation and prospective confirmation.
