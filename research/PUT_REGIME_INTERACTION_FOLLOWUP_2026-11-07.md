# PUT regime interaction follow-up — 2026-11-07

## Executive result

A potentially useful three-way regime emerged in the exploratory PUT proxy:

**positive prior 3×M5 momentum + ATR/close in the upper training-history quartile + ADX(14) < 25.**

At a fixed 92% payout, this subset produced 50 wins, 30 losses and 1 draw (80 decisive trades), +16.00 units. It outperformed the rest of the positive-momentum PUT signals descriptively. The same fixed threshold produced positive results in both chronological partitions.

This is a **hypothesis for prospective testing, not a validated strategy**. The regime was discovered after repeated analysis of this dataset; the historical holdout has already been inspected many times. Do not promote the nominal p-values to confirmatory evidence and do not deploy this filter in Desktop.

## Data and reproducibility

- Input: `eurusd_research_clean.csv`, 486,488 M1 observations.
- Timestamp convention: minute timestamps are bucketed into UTC-aligned five-minute groups; only complete groups retained.
- Result: 97,227 complete M5 bars, 68 continuous segments, 2025-07-21 to 2026-11-05.
- Signal proxy: prior M5 close above prior BB(20, 2 population-SD) upper band, current close re-enters below current upper band, Williams %R(14) crosses from >= -20 to < -20, and ADX(14) >= 15.
- Entry: next M5 open; settlement: next M5 close. No trades across gaps. Sequential signal scheduling allows a new signal on the prior trade's expiry candle close.
- Payout: +0.92 win, -1 loss, 0 draw.
- Indicators were calculated with Wilder-style EWM smoothing; this is a diagnostic reconstruction, not guaranteed bit-for-bit identical to the unavailable original screening code.
- Chronological 70/30 split by complete M5 bars: 2026-06-17 19:55 UTC. Train quantiles are estimated on eligible TRAIN bars only.
- All results below are exploratory, with no multiple-testing correction. Holdout has already been used in prior investigations.

## Broad PUT proxy result

The proxy generated 1,171 scheduled PUT trades: 1,141 decisive, 572 wins, 569 losses, 30 draws; net -28.64 units.

By prior 3-bar momentum:
| Momentum | Trades | Decisive | Wins | WR | Net |
|---|---:|---:|---:|---:|---:|
| UP | 893 | 869 | 449 | 51.67% | -6.92 |
| DOWN | 263 | 259 | 115 | 44.40% | -38.20 |
| FLAT | 15 | 13 | 5 | 38.46% | -3.40 |

The UP/DOWN difference is a descriptive association only. The UP group remains below the 52.0833% break-even threshold. Its matched all-bar next-candle DOWN baseline was 49.53% (47,242 eligible bars), giving +2.14 percentage points of lift; one-sided binomial p=0.110. DOWN-momentum baseline was 47.76% (47,793 bars), while the strategy achieved 44.40% (lift -3.36 pp).

## Three-way regime candidate

ATR/close 75th percentile estimated on TRAIN eligible bars only: **0.0003596314** (about 3.60 basis points). Fixed conditions:

1. prior 3×M5 close-to-close momentum > 0;
2. ATR(14)/close >= 0.0003596314;
3. ADX(14) < 25.

| Partition | Trades | Decisive | Wins | WR | Net at 92% |
|---|---:|---:|---:|---:|---:|
| Train | 60 | 60 | 35 | 58.33% | +7.20 |
| Holdout | 21 | 20 | 15 | 75.00% | +8.80 |
| Combined | 81 | 80 | 50 | 62.50% | +16.00 |

The remaining positive-momentum trades outside this regime:
- Train: 548 trades, 533 decisive, 51.03% WR, -10.76 units.
- Holdout: 264 trades, 256 decisive, 49.61% WR, -12.16 units.
- Combined: 812 trades, 789 decisive, 50.57% WR, -22.92 units.

Naive Fisher exact comparison within the UP-momentum subset: odds ratio 1.63, p=0.027. This is not confirmatory because the regime was selected after looking at the data and multiple candidate interactions were explored.

Matched background next-candle DOWN rates in the same three-way regime:
- Train: 3,885 eligible bars, 49.94% DOWN; strategy WR 58.33%, lift +8.40 pp; one-sided binomial p=0.121.
- Holdout: 877 eligible bars, 51.65% DOWN; strategy WR 75.00% (15/20), lift +23.35 pp; nominal one-sided binomial p=0.029.
The holdout p-value is especially vulnerable to selection bias and the small n=20 denominator; do not interpret it as proof.

## Month dispersion

The 81-trade candidate occurred in 17 calendar months. Monthly counts are small (1–13 trades); results varied substantially:
- Negative months included Jul-2025 (1/3), Aug-2025 (3/7), Sep-2025 (2/6), Feb-2026 (0/2), Sep-2026 (0/1).
- Strong positive months included Oct-2025 (4/5), Apr-2026 (5/7), Jun-2026 (5/6), Oct-2026 (8/10).
This is not yet evidence of stable month-to-month performance.

## Interpretation and decision

The interesting observation is not simply “PUT after an up move”. The broad UP-momentum subset loses money. The stronger candidate is a narrower combination: **positive short-term impulse, elevated realized range, but ADX still below 25**. One possible interpretation is a sharp upward excursion that has not matured into a strong directional trend, followed by upper-band re-entry. That interpretation is a hypothesis, not a demonstrated causal mechanism.

Actions:
1. Keep the candidate out of production and leave CALL frozen.
2. Freeze the exact thresholds and signal rules before any new data arrives.
3. Collect a genuinely prospective, untouched M1 sample; do not re-tune on it. Evaluate at 92% payout, same next-candle expiry, gap exclusions and non-overlap rules.
4. Require adequate sample size and performance across multiple weeks/months before considering integration. Include quote/spread/latency sensitivity before any real-money decision.
