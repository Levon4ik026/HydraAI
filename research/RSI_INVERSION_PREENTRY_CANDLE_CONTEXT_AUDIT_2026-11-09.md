# RSI Inversion — Pre-entry Candle and Context Feature Audit (2026-11-09)

## Executive summary

A causal feature screen was run on the RSI(14) inversion cohort, using only information available at the close of the signal candle. The most interesting result is a simple candle-shape condition:

**When the inverted CALL signal candle closes within 0.1 pip of its high (upper wick <= 0.1 pip), the 15-minute strategy is positive in TRAIN, VALIDATION and TEST.**

| Split | Trades | Wins | Losses | Draws | Decisive WR | Net at 92% payout |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,278 | 712 | 548 | 18 | 56.51% | +107.04u |
| VALIDATION | 340 | 178 | 156 | 6 | 53.29% | +7.76u |
| TEST | 312 | 181 | 120 | 11 | **60.13%** | **+46.52u** |

This is a research lead, not a validated or deployable strategy. The TEST result is encouraging, but the split was inspected in a broad feature screen, the sample is modest, and the TEST profit is concentrated in August. The threshold was selected using TRAIN, not tuned on TEST. The directional decomposition is exploratory.

A second, narrower result was found for inverted PUTs when price is 3.042–5.692 pips above EMA50 at the signal close. It was positive across all splits, but only 335 TEST trades and only one signal side. It is secondary to the upper-wick result.

## Data and protocol

- Dataset: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 BID candles.
- Coverage: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC; 68 continuity segments.
- SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- RSI: Wilder RSI(14), SMA seed over the first 14 changes within each continuity segment, then Wilder recursive smoothing.
- Signal: RSI crosses above 70 -> original CALL, inverted PUT; RSI crosses below 30 -> original PUT, inverted CALL.
- Signal known at signal candle close; entry at next M1 candle open; expiry at close of the 15th entry candle.
- One-position schedule per continuity segment: next signal eligible only after prior expiry candle. Each filtered strategy is independently scheduled; rejected signals do not block later eligible signals.
- TRAIN: before 2026-05-08. VALIDATION: 2026-05-08 through 2026-08-05. TEST: from 2026-08-06.
- Trades crossing split boundaries or data gaps excluded.
- Fixed hypothetical payout: +0.92u win, -1u loss, 0u draw. Break-even decisive WR = 52.0833%. Decisive WR excludes draws.
- All features are calculated from completed candles no later than the signal candle close. No future candles enter feature values.

### Cohort replication caveat

This implementation yields 5,199 TRAIN / 1,473 VALIDATION / 1,510 TEST scheduled baseline events. Earlier reports list 5,197 / 1,473 / 1,508. The remaining 2 TRAIN and 2 TEST event discrepancy is unresolved. This audit is internally consistent, but the original report generator should be found and unified before exact replication is claimed.

## Features screened

Twenty-one pre-entry feature series were examined:
- RSI level and RSI change over 1, 3 and 5 candles;
- signal candle return, range, absolute body, upper wick and lower wick;
- prior 3, 5, 10, 20 and 50-minute close momentum;
- close distance from EMA20 and EMA50;
- ATR14;
- distance to rolling 10- and 20-candle highs and lows.

For each feature, TRAIN quintile boundaries were computed. The quintile with the largest TRAIN net P&L (minimum 150 decisive TRAIN trades) was frozen and evaluated unchanged in VALIDATION and TEST. This is a broad exploratory screen, not a multiple-testing-corrected experiment.

## 1. Best TRAIN-selected single-feature bins

| Feature | Frozen TRAIN bin | TRAIN n / WR / net | VALIDATION n / WR / net | TEST n / WR / net |
|---|---|---:|---:|---:|
| Upper wick | <= 0.1 pip | 2,217 / 55.18% / +129.08u | 584 / 54.02% / +21.28u | 560 / 56.80% / +49.28u |
| RSI level | <= 28.025 | 1,040 / 57.50% / +106.72u | 313 / 55.70% / +21.24u | 302 / 51.00% / -6.00u |
| Lower wick | <= 0.1 pip | 2,109 / 54.30% / +89.84u | 535 / 54.70% / +26.88u | 570 / 54.10% / +21.84u |
| ATR14 | 0.779–1.086 pips | 1,038 / 56.60% / +88.60u | 355 / 51.40% / -4.40u | 381 / 48.70% / -24.48u |
| Signal candle range | <= 1.1 pips | 1,058 / 56.20% / +81.60u | 308 / 49.30% / -15.84u | 411 / 58.50% / +49.28u |
| RSI change, 3 candles | <= -10.957 RSI points | 1,039 / 56.00% / +77.92u | 312 / 54.40% / +13.64u | 298 / 57.80% / +31.72u |
| EMA50 distance | 3.042–5.692 pips | 1,035 / 55.70% / +69.72u | 317 / 55.30% / +19.16u | 335 / 58.10% / +37.72u |

The RSI-level and ATR filters failed on TEST despite good TRAIN results. This is a warning against selecting indicators from TRAIN P&L alone. Upper-wick, RSI 3-candle change, and EMA50 distance are more consistent across the three chronological splits, but still need fresh forward validation.

## 2. Upper-wick condition by inverted direction

The <=0.1-pip upper-wick condition is not equally useful for both signal directions.

| Split | Inverted side | Trades | Decisive WR | Net |
|---|---|---:|---:|---:|
| TRAIN | PUT | 939 | 53.34% | +22.04u |
| TRAIN | CALL | 1,278 | 56.51% | +107.04u |
| VALIDATION | PUT | 244 | 55.04% | +13.52u |
| VALIDATION | CALL | 340 | 53.29% | +7.76u |
| TEST | PUT | 248 | 52.67% | +2.76u |
| TEST | CALL | 312 | **60.13%** | **+46.52u** |

The strongest TEST component is inverted CALL: RSI crosses below 30, the inverted direction is CALL, and the signal candle closes at or within 0.1 pip of its high. The result is positive in TRAIN and VALIDATION too, but VALIDATION is only modestly above break-even. The side split is an exploratory decomposition and must be retested on new data.

### Inverted CALL <=0.1-pip upper wick, full split detail

| Split | Trades | W | L | D | Decisive WR | Net |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,278 | 712 | 548 | 18 | 56.51% | +107.04u |
| VALIDATION | 340 | 178 | 156 | 6 | 53.29% | +7.76u |
| TEST | 312 | 181 | 120 | 11 | 60.13% | +46.52u |

On TEST, the Wilson 95% interval for decisive WR is approximately 54.51%–65.50%. An unadjusted one-sided binomial test against 52.0833% gives p ≈ 0.0030. This p-value is not corrected for the feature/threshold search and should not be interpreted as confirmatory evidence.

A 20,000-replicate daily P&L block bootstrap over 70 TEST trading days gives a 95% percentile interval of approximately +18.80u to +73.76u. This is a descriptive resampling interval; it does not correct selection bias, regime concentration or data-source mismatch.

### TEST monthly split for inverted CALL <=0.1-pip upper wick

| Month | Trades | W | L | D | Decisive WR | Net |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08 | 85 | 57 | 24 | 4 | 70.37% | +28.44u |
| 2026-09 | 111 | 59 | 48 | 4 | 55.14% | +6.28u |
| 2026-10 | 106 | 59 | 44 | 3 | 57.28% | +10.28u |
| 2026-11 partial | 10 | 6 | 4 | 0 | 60.00% | +1.52u |

August contributes 28.44 of the 46.52 TEST units. September and October remain positive but materially weaker. November has only 10 trades and is not informative.

### Comparison with unfiltered inverted CALL baseline

| Split | Baseline trades | Baseline WR | Baseline net | Filtered trades | Filtered WR | Filtered net |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 2,639 | 54.27% | +109.72u | 1,278 | 56.51% | +107.04u |
| VALIDATION | 777 | 51.31% | -11.44u | 340 | 53.29% | +7.76u |
| TEST | 767 | 54.40% | +33.36u | 312 | 60.13% | +46.52u |

The filter cuts the CALL trade count by roughly half. TRAIN net is nearly unchanged despite fewer trades; validation turns slightly positive; TEST net improves. This is promising but not proof of a stable edge.

## 3. Secondary candidate: EMA50 distance for inverted PUT

The TRAIN-selected 3.042–5.692-pip EMA50 distance interval occurs only in the inverted PUT subset in this cohort.

| Split | Trades | W | L | D | Decisive WR | Net |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,035 | 566 | 451 | 18 | 55.65% | +69.72u |
| VALIDATION | 317 | 173 | 140 | 4 | 55.27% | +19.16u |
| TEST | 335 | 191 | 138 | 6 | 58.05% | +37.72u |

TEST monthly net: August +15.08u (81 trades), September +9.36u (105), October +15.24u (124), partial November -1.96u (25). This is a smaller candidate and should remain secondary.

## 4. Interpretation and decision

1. A signal candle with virtually no upper wick is associated with better inverted RSI outcomes. The relationship is clearest for inverted CALL signals.
2. A very small candle range also looked good on TEST but failed VALIDATION, so do not combine it with the upper-wick filter.
3. ATR14 bins are unstable and should not be used as a filter.
4. RSI level alone overfits: its TRAIN-selected low-RSI bin loses money on TEST.
5. EMA50 distance may be a separate useful context filter for inverted PUTs, but it is based on a narrower sample.
6. The current results use historical Dukascopy BID candles, not Pocket Option executable quotes. Actual payout variation, platform quote differences, latency and settlement rules are not modeled.
7. The feature search involved multiple features and bins. TEST is no longer a pristine untouched holdout after this exploratory inspection.

**Decision: retain two research leads only — (A) inverted CALL with upper wick <=0.1 pip; (B) inverted PUT with close 3.042–5.692 pips above EMA50. Do not add either to production HydraAI or trade them live.**

## Next validation gate

- Reconcile the 2 TRAIN / 2 TEST baseline event discrepancy with the original RSI report generator.
- Freeze the two candidate definitions exactly as written.
- Run a walk-forward validation on a genuinely new chronological period, preferably a fresh data collection period with platform-aligned quotes.
- Report results by month, session, volatility and payout level; no further threshold tuning on the current TEST period.
- Keep manual-analysis-only architecture; no automated trade execution.
