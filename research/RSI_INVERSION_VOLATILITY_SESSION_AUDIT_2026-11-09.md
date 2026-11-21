# RSI Inversion — Volatility and Session Regime Audit (2026-11-09)

## Executive result

The next diagnostic was to test whether the inverted RSI(14) crossing strategy behaves differently across volatility and UTC session regimes. The horizon was frozen at 15 minutes before this analysis; no expiry optimization was performed here.

A volatility split derived exclusively from TRAIN candles shows a consistent TRAIN/VALIDATION/TEST ordering:

- Low + middle volatility: positive net result in all three chronological splits.
- High volatility: negative net result in all three chronological splits.

This is a useful hypothesis, but not a validated filter. Within TEST, the low+middle volatility aggregate is still dominated by August 2026, and dependence-aware intervals cross zero for longer block lengths. No production change is justified.

## Data and exact specification

- Dataset: `eurusd_research_clean.csv`; 486,488 M1 bars; 68 uninterrupted segments.
- Coverage: 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- RSI: Wilder RSI(14), reset at each uninterrupted segment.
- Adverse/original interpretation: RSI crosses above 70 -> CALL; crosses below 30 -> PUT.
- Inversion: reverse both directions.
- Signal is known at signal candle close; entry is next M1 candle open; outcome is close of the 15th entry minute.
- One-position schedule per segment: a new signal is eligible when its signal candle timestamp is at or after the previous trade's expiry candle. This permits a signal on the previous expiry candle close, after that expiry has completed.
- Outcomes: directional close-vs-entry-open; ties are draws.
- Split: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06. Trades crossing split boundaries or data gaps are excluded.
- Fixed hypothetical payout: +0.92u win, -1u loss, 0u draw; break-even decisive WR 52.0833%.
- Historical Dukascopy BID bars only. No Pocket Option executable quote, changing payout, latency, or settlement simulation.

### Volatility definition frozen from TRAIN

At each signal candle close, calculate Wilder ATR(14) divided by close, in basis points. Compute one-third and two-third quantiles using all valid TRAIN candle observations only:

- LOW: ATR/close <= 0.85457 bp? (exact fraction below)
- MID: between the TRAIN 33.333% and 66.667% quantiles.
- HIGH: above the TRAIN 66.667% quantile.

Exact quantile values as ATR/close fractions:
- q33 = 0.0000854572605
- q66 = 0.000134769563

The thresholds are frozen; VALIDATION and TEST do not influence them. Note: these are ATR/close fractions; multiply by 10,000 to express basis points (0.85457 and 1.34770 bp).

## Main results: 15-minute inverted RSI by volatility

| Split | Volatility | Trades | W | L | D | Decisive WR | Net units |
|---|---|---:|---:|---:|---:|---:|---:|
| TRAIN | LOW | 1,730 | 936 | 746 | 48 | 55.65% | +115.12 |
| TRAIN | MID | 1,709 | 913 | 778 | 18 | 53.99% | +61.96 |
| TRAIN | HIGH | 1,758 | 904 | 847 | 7 | 51.63% | -15.32 |
| VALIDATION | LOW | 472 | 248 | 211 | 13 | 54.04% | +17.16 |
| VALIDATION | MID | 634 | 329 | 296 | 9 | 52.64% | +6.68 |
| VALIDATION | HIGH | 367 | 188 | 177 | 2 | 51.51% | -4.04 |
| TEST | LOW | 565 | 299 | 247 | 19 | 54.77% | +28.08 |
| TEST | MID | 541 | 298 | 236 | 7 | 55.98% | +38.16 |
| TEST | HIGH | 402 | 203 | 191 | 8 | 51.52% | -4.24 |

Combining LOW + MID (threshold fixed from TRAIN):

| Split | Trades | W | L | D | Decisive WR | Net units |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 3,439 | 1,849 | 1,524 | 66 | 54.82% | +177.08 |
| VALIDATION | 1,106 | 577 | 507 | 22 | 53.23% | +23.84 |
| TEST | 1,106 | 597 | 483 | 26 | 55.28% | +66.24 |

The directional ordering (LOW/MID better than HIGH) is consistent across all three chronological splits. This is the strongest result of this regime audit. However, the combined TEST result does not mean a robust strategy has been established.

## Important caveat: low/mid TEST result remains month-concentrated

| Month | LOW+MID trades | W | L | D | Decisive WR | Net units |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08 | 320 | 194 | 116 | 10 | 62.58% | +62.48 |
| 2026-09 | 413 | 208 | 193 | 12 | 51.87% | -1.64 |
| 2026-10 | 324 | 170 | 150 | 4 | 53.13% | +6.40 |
| 2026-11 partial | 49 | 25 | 24 | 0 | 51.02% | -1.00 |

August still contributes nearly all of the low/mid-volatility TEST profit. September and partial November are negative; October is only modestly positive. Therefore the volatility split has not solved the temporal stability problem.

## Dependence-aware uncertainty: LOW+MID TEST

Daily P&L was aggregated over every calendar day from 2026-08-06 through 2026-11-05, including zero-trade days. Circular moving-block bootstrap: 20,000 replicates per block length, fixed seed 20261109 + block length.

| Block length | 95% interval for cumulative P&L | Bootstrap share <= 0 |
|---:|---:|---:|
| 3 days | +8.00 to +124.56u | 1.31% |
| 5 days | +3.40 to +131.24u | 1.96% |
| 10 days | -6.88 to +139.12u | 3.82% |
| 15 days | -16.32 to +147.40u | 5.91% |

Longer blocks include zero. This reinforces that the observed result is uncertain and sensitive to the persistence of market regimes. Bootstrap results are descriptive, not a formal guarantee.

## UTC session diagnostics (not selected as filters)

Sessions were defined mechanically in UTC: Asia 00:00–06:59, London 07:00–12:59, New York 13:00–20:59, late 21:00–23:59.

| Split | Session | Trades | Decisive WR | Net units |
|---|---|---:|---:|---:|
| TRAIN | Asia | 1,525 | 53.02% | +26.64 |
| TRAIN | London | 1,322 | 55.57% | +87.76 |
| TRAIN | New York | 1,710 | 51.08% | -33.12 |
| TRAIN | Late | 640 | 58.75% | +80.48 |
| VALIDATION | Asia | 439 | 52.34% | +2.16 |
| VALIDATION | London | 401 | 53.17% | +8.20 |
| VALIDATION | New York | 469 | 49.03% | -27.32 |
| VALIDATION | Late | 164 | 64.00% | +36.76 |
| TEST | Asia | 480 | 51.29% | -7.04 |
| TEST | London | 396 | 53.08% | +7.44 |
| TEST | New York | 471 | 56.19% | +37.20 |
| TEST | Late | 161 | 60.13% | +24.40 |

Session effects are not stable: New York is negative in TRAIN and VALIDATION but positive in TEST; late session is positive in all splits but has a much smaller sample and is sensitive to a small number of observations. Do not use session filters based on this screen.

## Decision

**Status: RESEARCH CANDIDATE — VOLATILITY CONDITIONING HYPOTHESIS, NOT VALIDATED.**

Evidence worth following:
- High-volatility bucket is below the 92%-payout break-even rate in TRAIN, VALIDATION and TEST.
- LOW+MID bucket is above break-even in all three splits.

Evidence against premature acceptance:
- TEST LOW+MID P&L is dominated by August.
- 10- and 15-day block-bootstrap intervals include zero.
- This is one of several exploratory diagnostics; multiple-testing and selection bias remain.
- Fixed 92% payout and BID-only prices are simplifications.

## Next step

Do not tune the ATR cutoffs or search for a better RSI period on this TEST set. Freeze this exact volatility definition and collect a genuinely new, later sample. In parallel, test the hypothesis on demo-captured Pocket Option quotes with the actual payout attached to each signal. Until then, keep it out of the production dashboard and do not automate it.