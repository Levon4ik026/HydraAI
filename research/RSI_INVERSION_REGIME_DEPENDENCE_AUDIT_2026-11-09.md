# RSI Inversion — Regime and Dependence Audit (2026-11-09)

## Executive summary

The first screen's RSI(14) inverted crossing rule reproduces on the cleaned EUR/USD M1 dataset. The apparent 15-minute TEST advantage is not robust enough to accept as a stable edge:

- TEST: 1,508 scheduled trades, 800 wins, 674 losses, 34 draws; decisive win rate 54.27%; hypothetical net +62.00 units at fixed 92% payout.
- However, 360 of those trades occurred in August 2026 and produced +63.80 units by themselves. September was only +5.60, October was -8.16, and the partial November sample +0.76.
- A calendar-day moving-block bootstrap of daily P&L gives a 95% interval for cumulative TEST P&L that crosses zero for block lengths 5, 10 and 15 days. This is consistent with substantial temporal dependence and uncertainty.
- The result is therefore a promising research clue, not a validated trading edge. Do not deploy it.

## Dataset and reproducibility

- File: `eurusd_research_clean.csv`
- Rows: 486,488 M1 bars
- Coverage: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC
- SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`
- 68 uninterrupted minute-continuity segments.
- Indicator: RSI(14), Wilder smoothing, reset at each segment.
- Original intentionally adverse rule: RSI crosses above 70 -> CALL; crosses below 30 -> PUT.
- Inversion: reverse each signal direction.
- Signal at candle close; entry at next M1 open; expiry at close after 1/3/5/10/15/20 minutes.
- One-position schedule per rule and segment; next signal eligible at/after prior expiry candle close.
- Splits: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06. Trades crossing a split boundary or data gap are excluded.
- Outcome: directional close-vs-entry-open. Draws excluded from decisive WR.
- Hypothetical fixed payout: +0.92u win, -1u loss, 0u draw; break-even decisive WR 52.0833%.
- Historical Dukascopy BID bars only; not Pocket Option execution quotes.

## Reproduced split results: inverted RSI

| Expiry | Split | Trades | W | L | D | Decisive WR | Net units |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1m | TRAIN | 8,115 | 4,037 | 3,605 | 473 | 52.83% | +109.04 |
| 1m | VALIDATION | 2,281 | 1,137 | 1,016 | 128 | 52.81% | +30.04 |
| 1m | TEST | 2,359 | 1,164 | 1,060 | 135 | 52.34% | +10.88 |
| 3m | TRAIN | 7,676 | 3,935 | 3,486 | 255 | 53.03% | +134.20 |
| 3m | VALIDATION | 2,162 | 1,112 | 967 | 83 | 53.49% | +56.04 |
| 3m | TEST | 2,231 | 1,127 | 1,017 | 87 | 52.57% | +19.84 |
| 5m | TRAIN | 6,947 | 3,655 | 3,136 | 156 | 53.82% | +226.60 |
| 5m | VALIDATION | 1,941 | 997 | 890 | 54 | 52.84% | +27.24 |
| 5m | TEST | 1,992 | 1,010 | 925 | 57 | 52.20% | +4.20 |
| 10m | TRAIN | 5,834 | 3,078 | 2,637 | 119 | 53.86% | +194.76 |
| 10m | VALIDATION | 1,627 | 897 | 693 | 37 | 56.42% | +132.24 |
| 10m | TEST | 1,704 | 892 | 782 | 30 | 53.29% | +38.64 |
| 15m | TRAIN | 5,197 | 2,753 | 2,371 | 73 | 53.73% | +161.76 |
| 15m | VALIDATION | 1,473 | 765 | 684 | 24 | 52.80% | +19.80 |
| 15m | TEST | 1,508 | 800 | 674 | 34 | 54.27% | +62.00 |
| 20m | TRAIN | 4,739 | 2,547 | 2,128 | 64 | 54.48% | +215.24 |
| 20m | VALIDATION | 1,351 | 727 | 606 | 18 | 54.54% | +62.84 |
| 20m | TEST | 1,391 | 738 | 637 | 16 | 53.67% | +41.96 |

## Critical regime breakdown: 15-minute TEST

| Month | Trades | W | L | D | Decisive WR | Net units |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08 | 360 | 215 | 134 | 11 | 61.60% | +63.80 |
| 2026-09 | 499 | 255 | 229 | 15 | 52.69% | +5.60 |
| 2026-10 | 548 | 277 | 263 | 8 | 51.30% | -8.16 |
| 2026-11 partial | 101 | 53 | 48 | 0 | 52.48% | +0.76 |

The August profit exceeds the total TEST profit. The aggregate result conceals that the following months were near break-even or negative. This is the most important warning in the audit.

## Directional component check

For the 15-minute TEST:
- Inverted signals originating from the original RSI-down-through-30 PUT rule: 766 trades, 54.21% decisive WR, +30.52u.
- Inverted signals originating from the original RSI-up-through-70 CALL rule: 742 trades, 54.34% decisive WR, +31.48u.

The aggregate edge is not solely attributable to one crossing direction. But the monthly component results are unstable: for example, the inverted oversold-side component was negative in September and October, while the inverted overbought-side component was positive in September and close to flat in October. No stable side-specific mechanism is established.

## Dependence-aware uncertainty check

For the 15-minute TEST, daily P&L was aggregated over the full calendar span 2026-08-06 through 2026-11-05, including zero-trade days. A circular moving-block bootstrap resampled contiguous calendar-day blocks (20,000 replicates; fixed random seed 20261109) to preserve some short-range temporal clustering.

| Block length | 95% interval for resampled cumulative P&L | Share of bootstrap totals <= 0 |
|---:|---:|---:|
| 3 calendar days | -3.16 to +126.00u | 3.11% |
| 5 calendar days | -10.16 to +134.84u | 4.63% |
| 10 calendar days | -21.64 to +147.00u | 7.82% |
| 15 calendar days | -31.36 to +155.44u | 10.30% |

The interval crosses zero at 5/10/15-day blocks. The bootstrap is descriptive and sensitive to block choice; it is not a formal proof or a substitute for a genuinely untouched future sample. It shows why naive trade-level binomial confidence intervals would overstate certainty.

## Decision

**Status: RESEARCH CANDIDATE — NOT VALIDATED.**

The inverse RSI rule is worth keeping on the research shortlist because its chronological TRAIN, VALIDATION and TEST aggregates are positive under the simplified fixed-payout model. But the monthly breakdown and block bootstrap do not support treating the aggregate TEST gain as stable. August appears to dominate the apparent advantage.

## Next experiment (pre-registered direction)

Do not optimize RSI thresholds, period, or expiry on this same TEST set. Instead:

1. Freeze the existing RSI(14), 70/30 cross rules and 15-minute horizon as the candidate specification for a prospective/untouched evaluation; do not choose the best expiry again.
2. Measure pre-signal volatility using a causal ATR/realized-volatility measure and define bins from TRAIN quantiles only. Test whether the inversion effect is regime-conditioned on VALIDATION/TEST without selecting a winning bin after seeing TEST.
3. Add time-of-day/session and weekday breakdowns as diagnostics, not as a new optimization search.
4. Use date-block bootstrap and a final untouched later period once available.
5. Repeat on Pocket Option demo-captured quotes with observed payout per event. BID-only historical data cannot validate platform execution, quote differences, or payout.

No production files were modified.