# PUT prior-momentum interaction check — 2026-11-07

## Verdict

The earlier observation on the 376-trade legacy PUT holdout (352 trades after positive M5 momentum, 24 after negative momentum) is **not yet validated as a property of the original strategy**. The original signal-generation source and training timestamps are unavailable. A separate, reproducible full-history BB(20,2)+Williams %R(14) re-entry implementation was therefore evaluated as a diagnostic proxy. It shows a similar *relative* ordering (PUTs after positive momentum perform better than PUTs after negative momentum), but neither group is profitable at 92% payout, neither beats its matched unconditional direction baseline significantly, and the result is not a usable filter.

No production/Desktop code was changed. CALL remains untouched.

## Data and protocol

- Source: `eurusd_research_clean.csv`, 486,488 M1 rows, 2025-07-21 through 2026-11-05.
- Rebuilt 97,227 complete UTC-aligned M5 candles in 68 continuous segments. Incomplete buckets and trades crossing gaps were excluded.
- Reconstructed diagnostic signal: BB(20, 2 population SD) re-entry from above upper band to below upper band, simultaneous Williams %R(14) cross from >= -20 to < -20; ADX(14) >= 15.
- Entry: next M5 candle open; settlement: that candle close; shared sequential non-overlap scheduler; 92% payout (+0.92/-1/0).
- Prior impulse: close-to-close change over the preceding 3 M5 bars, classified UP/DOWN/FLAT.
- The indicator calculation used pandas Wilder-style EWM approximations, not the exact seeded Wilder implementation in `reproduce_m5_bb_williams_adx.py`. Treat this as a proxy diagnostic, not bit-for-bit reproduction.
- Chronological split by M5 bars at 70%: 2026-06-17 05:00 UTC. Trades assigned by signal time; the old 376-trade file's original rule is not reconstructed by this proxy.
- All thresholds and groupings are exploratory. No confirmatory claim is made from this already-inspected history.

## Full-history proxy results — PUT only

| Prior 3-bar momentum | Trades | Decisive | Wins | WR | Net at 92% |
|---|---:|---:|---:|---:|---:|
| UP | 893 | 869 | 449 | 51.67% | -6.92 |
| DOWN | 263 | 259 | 115 | 44.40% | -38.20 |
| FLAT | 15 | 13 | 5 | 38.46% | -3.40 |

The UP vs DOWN win-rate difference is 7.27 percentage points. Naive two-sided Fisher exact p=0.0473 (449/420 vs 115/144). This is an unadjusted, post-hoc comparison: it ignores temporal clustering, regime dependence and the many exploratory comparisons. It is not confirmatory evidence.

More importantly, the matched background next-candle DOWN rates among all eligible M5 bars were:
- Prior momentum UP: 49.68% (n=39,102); strategy PUT WR 51.67%, lift +1.99 pp.
- Prior momentum DOWN: 47.81% (n=39,746); strategy PUT WR 44.40%, lift -3.41 pp.

One-sided binomial tests against these descriptive background rates are not significant (UP p=0.128; DOWN p=0.150). The strategy does not cross the 52.0833% break-even threshold in either momentum state. Wilson 95% interval for UP WR: 48.35–54.98%; DOWN WR: 38.48–50.49%.

## Chronological stability

| Period | Momentum | Trades | Decisive | WR | Net |
|---|---|---:|---:|---:|---:|
| Train | UP | 608 | 593 | 51.77% | -3.56 |
| Train | DOWN | 172 | 169 | 43.79% | -26.92 |
| Holdout | UP | 285 | 276 | 51.45% | -3.36 |
| Holdout | DOWN | 91 | 90 | 45.56% | -11.28 |

The relative ordering repeats in both chronological partitions, but the UP group remains below break-even in both. This supports only a weak ranking hypothesis, not a profitable PUT rule.

## Volatility × ADX check

Volatility split at the full-sample median ATR/close; ADX split at 25. This is descriptive and post-hoc.

| Volatility | ADX | Trades | Decisive | WR | Net |
|---|---|---:|---:|---:|---:|
| High | >=25 | 306 | 298 | 49.66% | -13.84 |
| High | <25 | 280 | 275 | 52.36% | +1.48 |
| Low | >=25 | 228 | 221 | 50.68% | -5.96 |
| Low | <25 | 357 | 347 | 47.55% | -30.20 |

This does **not** reproduce the earlier apparent high-volatility/high-ADX advantage. The best cell is high volatility with ADX <25, but it is only +0.28 pp above break-even and is not independently validated.

## Monthly behavior

The UP-momentum proxy PUT subset was positive in only 8 of 17 calendar months (July 2025 through partial November 2026); it had pronounced negative months including November 2025 (-15.64), February 2026 (-15.08), March 2026 (-14.16), and September 2026 (-12.80). The DOWN subset was negative overall. The positive-momentum subset therefore does not provide stable profitability.

## Research decision

1. Do not add a positive-momentum filter to production.
2. Do not interpret the p=0.0473 comparison as confirmation; it is post-hoc and not corrected for multiple comparisons or time clustering.
3. The original 376-trade legacy strategy still needs its exact source/timestamps to test its own momentum interaction. The proxy signal's trade set is different.
4. A valid next test requires a frozen hypothesis and a genuinely forward, untouched collection period (or a carefully designed walk-forward with all tuning confined to earlier windows). Keep the 92% payout and non-overlap/gap rules fixed.
