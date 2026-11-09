# RSI Inversion — Post-Signal Price Path Audit (2026-11-09)

## Purpose

Inspect what price does after an inverted RSI(14) signal, rather than judging only the final expiry close. This is an exploratory path audit, not a new strategy or a production change.

## Data and method

- Dataset: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 BID candles.
- Coverage: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC; 68 continuity segments.
- Signal: RSI(14) Wilder smoothing; cross above 70 is inverted to PUT, cross below 30 inverted to CALL.
- Signal is known at candle close; entry at next M1 open.
- 15-minute schedule: one open position per continuity segment; subsequent signal allowed after prior 15-minute expiry candle has closed.
- For each event, calculate signed close displacement each minute through minute 20, maximum favorable excursion (MFE), and maximum adverse excursion (MAE) using intraminute high/low over the first 15 entry candles.
- Split by signal timestamp: TRAIN before 2026-05-08; VALIDATION 2026-05-08 to 2026-08-05; TEST from 2026-08-06.
- This path audit uses a fresh standalone Wilder-RSI implementation. It produces 5,190 TRAIN / 1,472 VALIDATION / 1,509 TEST scheduled events. The previous summary report listed 5,197 / 1,473 / 1,508. The 7–9 event discrepancy indicates a small implementation/scheduling difference in the prior screen; this report does not silently force the counts to match. The broad path findings below are descriptive and should be reconciled against the original screening script before formal confirmation.

## 15-minute path summary

MFE and MAE are measured from entry open to the best/worst intrabar price within the 15-minute holding window, in pips (1 pip = 0.0001).

| Split | Events | Mean MFE | Median MFE | Mean MAE | Median MAE | MFE > MAE | Both favorable and adverse sides touched |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 5,190 | 3.49 | 2.50 | 3.35 | 2.10 | 53.18% | 92.78% |
| VALIDATION | 1,472 | 2.88 | 2.20 | 2.88 | 1.85 | 53.80% | 92.39% |
| TEST | 1,509 | 2.85 | 2.00 | 2.85 | 1.90 | 53.21% | 93.64% |

Interpretation:
- Favorable and adverse excursions are almost equal in every split.
- More than 92% of events touch both sides of the entry price within 15 minutes. This means a simple “price first moved our way” story is not established by final expiry results.
- MFE > MAE occurs in only about 53% of cases. The path edge is small.
- The intrabar high/low sequence is unknown from OHLC candles. We cannot infer whether favorable or adverse excursion happened first inside a given minute.

## Average signed close displacement through time

Positive values mean the close is in the direction of the inverted signal relative to entry open. Values are average pips per event.

| Minute | TRAIN | VALIDATION | TEST |
|---:|---:|---:|---:|
| 1 | +0.030 | +0.021 | +0.014 |
| 3 | +0.085 | +0.015 | -0.006 |
| 5 | +0.105 | -0.007 | +0.029 |
| 10 | +0.169 | +0.051 | +0.099 |
| 15 | +0.221 | +0.105 | +0.195 |
| 20 | +0.251 | +0.142 | +0.168 |

Mean displacement is positive by minute 15 in all splits in this independent replication, but it is very small in absolute price terms. It is not directly equivalent to binary-option win expectancy because the expiry outcome is based on the exact close and payout, and actual platform quotes are not modeled.

### Percentage of positive signed closes at selected minutes

| Minute | TRAIN | VALIDATION | TEST |
|---:|---:|---:|---:|
| 1 | 49.63% | 50.34% | 49.24% |
| 5 | 52.52% | 51.02% | 51.16% |
| 10 | 52.62% | 55.03% | 52.55% |
| 15 | 52.99% | 51.90% | 53.15% |
| 20 | 53.95% | 53.33% | 53.88% |

There is no convincing immediate directional response. The first minute is around 50% or below. The directional proportion gradually improves toward longer horizons, but the trajectory is not monotonic.

## TEST month path diagnostics at 15 minutes

| Month | Events | Mean MFE (pips) | Mean MAE (pips) | MFE > MAE |
|---|---:|---:|---:|---:|
| 2026-08 | 361 | 3.07 | 2.91 | 55.68% |
| 2026-09 | 499 | 2.84 | 2.84 | 53.91% |
| 2026-10 | 548 | 2.73 | 2.78 | 51.46% |
| 2026-11 partial | 101 | 2.95 | 2.85 | 51.49% |

This is consistent with the earlier observation that August's path behavior was more favorable, while October was weaker. It does not establish a causal regime explanation.

## What this does and does not tell us

1. The inverted RSI does not produce a clean immediate reversal. Price commonly moves both for and against the signal during the holding window.
2. Favorable and adverse excursion magnitudes are nearly balanced; any potential edge is subtle and appears more in the expiry close distribution than in a large intraday excursion asymmetry.
3. M1 OHLC cannot resolve within-minute event ordering. A stop/target simulation or “first touch” claim would be invalid without tick data.
4. The small discrepancy in event counts versus the prior screen must be reconciled before using this path audit as an exact replication of the earlier report.
5. Data are historical BID candles, not Pocket Option execution quotes; actual payout, spread, latency and settlement are not modeled.

## Next research gate

Before testing more filters, reconcile the original RSI event generator and schedule against this independent implementation so both scripts produce identical event timestamps. Then freeze the cohort and perform a causal, minute-by-minute conditional study using only information available at signal/entry time. Avoid selecting thresholds on TEST. No production strategy should be enabled from this result.