# RSI Inversion Candidates — Session, Volatility, Momentum and Payout Stress Test (2026-11-09)

## Executive conclusion

This audit attempted to verify both candidates from the prior pre-entry feature report. It uncovered a material reproducibility problem:

**Candidate A (inverted CALL when upper wick <= 0.1 pip) does not reproduce under the literal stated definition.** In the supplied 486,488-row dataset, this condition occurs only 23 raw RSI-cross events before the one-position schedule, not 1,278 TRAIN / 340 VALIDATION / 312 TEST trades. Exact high==close occurs only 8 times among raw inverted CALL crosses. Therefore the prior Candidate A headline cannot be relied upon until its feature units/calculation are recovered from the original script. It is withdrawn from consideration for now.

Candidate B (inverted PUT with close 3.042–5.692 pips above EMA50) is directionally reproducible but counts differ from the previous report. Under the independent implementation below, the result is positive in all three chronological splits and remains positive at 85%, 90%, and 92% payouts. However, the result is not stable across volatility regimes or months, and session differences are inconsistent. Candidate B remains a research lead only, not a deployable strategy.

## Data and implementation

- Dataset: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 BID candles.
- Coverage: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC; 68 continuity segments.
- SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- Continuity: a new segment begins whenever adjacent timestamps are not exactly 60 seconds apart.
- RSI(14): Wilder smoothing, SMA seed from first 14 changes in each segment.
- EMA50: recursive EMA, span 50, initialized from first close in each segment.
- Signal known at candle close; entry at next candle open; 15-minute outcome at close of the 15th entry candle.
- One-position schedule per candidate: next signal can occur at or after the previous expiry candle index. Trades crossing a data gap or split boundary are excluded.
- TRAIN: signal timestamp before 2026-05-08. VALIDATION: 2026-05-08 through 2026-08-05. TEST: from 2026-08-06.
- Directional outcome compares expiry close with entry open. Draws excluded from decisive win rate.
- Net units are calculated as W × payout − L, with draws = 0. No stake compounding or platform execution costs.
- Session buckets use UTC signal hour: ASIA 00:00–06:59, LONDON 07:00–12:59, NY 13:00–21:59, ROLLOVER 22:00–23:59. These are coarse UTC bins, not DST-adjusted exchange sessions.

This is an independent reproduction. Earlier RSI event reports had small unresolved event-count discrepancies. The present audit does not claim exact replication of those scripts.

## 1. Candidate A literal-definition audit

Prior report definition: inverted CALL when RSI crosses below 30 and signal candle upper wick is no greater than 0.1 pip.

Upper wick is explicitly calculated as `(high - close) / 0.0001`, i.e. in EUR/USD pips.

- Raw RSI-cross-below-30 events: 6,487.
- Raw events with upper wick <= 0.1 pip: **23**.
- Raw events with high exactly equal to close: 8.

The previous report stated 1,278 scheduled TRAIN / 340 VALIDATION / 312 TEST trades under the <=0.1-pip upper-wick rule. These figures cannot be reproduced from the literal unit definition. This is a material unit or feature-definition ambiguity, not a rounding issue.

**Decision:** withdraw Candidate A's reported performance pending recovery of the exact feature calculation and original script. Do not use the 60.13% headline or put this rule into HydraAI.

## 2. Candidate B reproduction

Definition: inverted PUT when RSI crosses above 70 and signal close is 3.042–5.692 pips above EMA50.

| Split | Trades | Wins | Losses | Draws | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,122 | 606 | 496 | 20 | 54.99% | +61.52u |
| VALIDATION | 349 | 194 | 151 | 4 | 56.23% | +27.48u |
| TEST | 371 | 203 | 162 | 6 | 55.62% | +24.76u |

Counts differ from the previous report (1,035 / 317 / 335). Likely causes include event-generation/scheduling and EMA initialization details; exact reconciliation remains open. The current result is internally consistent and uses the stated EMA-distance units.

### Payout sensitivity

| Split | Net @85% | Net @90% | Net @92% |
|---|---:|---:|---:|
| TRAIN | +19.10u | +49.40u | +61.52u |
| VALIDATION | +13.90u | +23.60u | +27.48u |
| TEST | +10.55u | +20.70u | +24.76u |

The observed win rates are above the corresponding break-even levels: 54.05% at 85%, 52.63% at 90%, and 52.08% at 92%. This is a historical arithmetic sensitivity only; actual per-trade payout, platform quote differences and settlement are not represented.

### TEST month-by-month

| Month | Trades | Wins | Losses | Draws | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08 | 88 | 51 | 35 | 2 | 59.30% | +11.92u |
| 2026-09 | 118 | 63 | 52 | 3 | 54.78% | +5.96u |
| 2026-10 | 136 | 74 | 61 | 1 | 54.81% | +7.08u |
| 2026-11 partial | 29 | 15 | 14 | 0 | 51.72% | -0.20u |

August is strongest, but unlike the prior Candidate A claim, the profit is not exclusively concentrated in one month. The partial November sample is slightly negative.

## 3. UTC session audit for Candidate B

| Split | Session | Trades | W | L | D | Decisive WR | Net @92% |
|---|---|---:|---:|---:|---:|---:|---:|
| TRAIN | Asia | 406 | 217 | 176 | 13 | 55.22% | +23.64u |
| TRAIN | London | 291 | 163 | 124 | 4 | 56.79% | +25.96u |
| TRAIN | NY | 341 | 173 | 165 | 3 | 51.18% | -5.84u |
| TRAIN | Rollover | 84 | 53 | 31 | 0 | 63.10% | +17.76u |
| VALIDATION | Asia | 118 | 68 | 47 | 3 | 59.13% | +15.56u |
| VALIDATION | London | 103 | 54 | 49 | 0 | 52.43% | +0.68u |
| VALIDATION | NY | 111 | 59 | 51 | 1 | 53.64% | +3.28u |
| VALIDATION | Rollover | 17 | 13 | 4 | 0 | 76.47% | +7.96u |
| TEST | Asia | 122 | 62 | 58 | 2 | 51.67% | -0.96u |
| TEST | London | 117 | 69 | 46 | 2 | 60.00% | +17.48u |
| TEST | NY | 119 | 64 | 53 | 2 | 54.70% | +5.88u |
| TEST | Rollover | 13 | 8 | 5 | 0 | 61.54% | +2.36u |

There is no single session that is consistently best across all splits. Asia is positive in TRAIN and VALIDATION but approximately flat/negative in TEST. London is positive in all three, though VALIDATION is barely above break-even. Rollover sample sizes are small. No session filter is justified from this table.

## 4. Volatility regime audit

ATR14 thresholds were calculated from TRAIN candidate trades only:
- LOW: ATR <= 0.9505 pips
- MID: 0.9505–1.2139 pips
- HIGH: ATR > 1.2139 pips

| Split | ATR bucket | Trades | W | L | D | Decisive WR | Net @92% |
|---|---|---:|---:|---:|---:|---:|---:|
| TRAIN | LOW | 374 | 216 | 146 | 12 | 59.67% | +52.72u |
| TRAIN | MID | 374 | 203 | 167 | 4 | 54.86% | +19.76u |
| TRAIN | HIGH | 374 | 187 | 183 | 4 | 50.54% | -10.96u |
| VALIDATION | LOW | 73 | 41 | 31 | 1 | 56.94% | +6.72u |
| VALIDATION | MID | 127 | 75 | 49 | 3 | 60.48% | +20.00u |
| VALIDATION | HIGH | 149 | 78 | 71 | 0 | 52.35% | +0.76u |
| TEST | LOW | 92 | 47 | 43 | 2 | 52.22% | +0.24u |
| TEST | MID | 132 | 70 | 59 | 3 | 54.26% | +5.40u |
| TEST | HIGH | 147 | 86 | 60 | 1 | 58.90% | +19.12u |

The TRAIN pattern suggests high volatility is harmful, but TEST shows the opposite: HIGH volatility is the strongest bucket. The low-volatility edge nearly disappears on TEST. This is a clear regime-dependence warning. Do not apply an ATR filter.

## 5. Previous momentum audit

At the signal close, calculate close-to-close momentum over 5 and 15 prior M1 bars. For Candidate B, nearly every event already has positive 5- and 15-minute momentum because the signal condition selects a close materially above EMA50.

TEST:
- 5-minute momentum UP: 368 trades, 56.08% WR, +27.76u; DOWN: only 3 trades.
- 15-minute momentum UP: 371 trades, 55.62% WR, +24.76u; no DOWN observations.

These features have virtually no discriminating power within this candidate cohort. They should not be used as additional filters.

## 6. Decision and next gate

1. Candidate A is invalidated as currently documented because the stated <=0.1-pip wick condition does not reproduce its reported sample count.
2. Candidate B reproduces as a modest positive historical candidate under this independent implementation and remains positive in all three splits at 85%, 90%, and 92% payout arithmetic.
3. Candidate B's volatility profile reverses between TRAIN and TEST; do not add an ATR filter.
4. Session effects are inconsistent; do not add a session filter.
5. Prior momentum is almost constant within Candidate B; do not add a momentum filter.
6. Event-count discrepancies with prior reports remain unresolved, so no claim of exact replication is made.
7. No production code or automatic execution was changed.

**Status:** Candidate B only — research lead, not validated. Candidate A withdrawn pending code/units reconciliation.

The next necessary action is to recover the exact earlier feature-generation script and reconcile RSI event timestamps, EMA initialization, feature units and trade scheduling. Until then, additional optimization risks building on inconsistent definitions.
