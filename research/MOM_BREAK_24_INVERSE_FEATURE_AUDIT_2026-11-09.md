# MOM_BREAK_24 inverse — frozen TRAIN feature audit (2026-11-09)

## Question
Does the inverse PUT result improve when the original bullish breakout has a particular shape (breakout overshoot, candle body/range, wick, prior range, trend or volatility)?

## Data and exact replay
- Input: `eurusd_research_clean.csv`, 486,488 valid EUR/USD M1 BID rows.
- Complete UTC-aligned M5 bars: 97,227 across 68 continuity segments.
- Candidate: MOM_BREAK_24_CALL inverted to PUT.
- Signal: completed M5 close above the highest high of the preceding 24 M5 bars, with a bullish candle.
- Entry: next M5 open. Settlement: close of the fourth subsequent M5 bar (20 minutes after entry).
- One-position schedule per strategy/expiry/segment; next signal eligible at the prior expiry bar's close.
- Split: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06. Trades settling across a split boundary are purged.
- Replay reproduction: TRAIN 1,848 (978W/840L/30D), VALIDATION 504 (270/222/12), TEST 521 (294/221/6). This matches the corrected inversion replay.
- Accounting at a hypothetical fixed 92% payout: W +0.92u, L -1u, D 0u; break-even decisive WR 52.0833%.

## Feature construction
All features are computed only from information available at the completed signal candle, within each continuous segment:
- `excess_pips`: close minus prior 24-bar highest high, in pips.
- `excess_atr`: same overshoot divided by rolling 14-bar mean true range.
- `body_atr`, `range_atr`: candle body/range divided by ATR.
- `upper_wick_ratio`, `close_pos`: upper wick share of range and close location within candle range.
- `prior24_range_atr`: previous 24-bar high-low range divided by ATR.
- `trend24_atr`: close-to-close change over 24 bars divided by ATR.
- `atr_pips`: ATR in pips.

For each feature, quartile boundaries were estimated on TRAIN only and then frozen for VALIDATION and TEST. No thresholds were chosen using TEST. This is a descriptive screen of nine related features; it is not a pre-registered confirmatory test and no multiple-testing correction is applied.

## Key feature-bin results
Decisive win rate; net units at 92% payout. Q1–Q4 are TRAIN-defined quartiles.

### Breakout overshoot in pips
TRAIN quartile boundaries: 0.40 / 1.00 / 2.20 pips.
| Period | Bin | n | W/L/D | Decisive WR | Net u |
|---|---|---:|---:|---:|---:|
| TRAIN | Q1 | 484 | 233/246/5 | 48.64% | -31.64 |
| TRAIN | Q2 | 446 | 226/208/12 | 52.07% | -0.08 |
| TRAIN | Q3 | 460 | 237/215/8 | 52.43% | +3.04 |
| TRAIN | Q4 | 458 | 282/171/5 | 62.25% | +88.44 |
| VALIDATION | Q1 | 148 | 75/68/5 | 52.45% | +1.00 |
| VALIDATION | Q2 | 127 | 69/56/2 | 55.20% | +7.48 |
| VALIDATION | Q3 | 119 | 69/48/2 | 58.97% | +15.48 |
| VALIDATION | Q4 | 110 | 57/50/3 | 53.27% | +2.44 |
| TEST | Q1 | 152 | 88/62/2 | 58.67% | +18.96 |
| TEST | Q2 | 157 | 92/64/1 | 58.97% | +20.64 |
| TEST | Q3 | 124 | 64/59/1 | 52.03% | -0.12 |
| TEST | Q4 | 88 | 50/36/2 | 58.14% | +10.00 |

The strong monotonic TRAIN relationship does not replicate: VALIDATION peaks in Q3, while TEST is positive in Q1/Q2/Q4 and weak in Q3. “Bigger overshoot = stronger reversal” is not supported as a stable rule.

### Normalized overshoot (excess / ATR)
TRAIN quartile boundaries: 0.1545 / 0.3516 / 0.6829 ATR.
| Period | Bin | n | W/L/D | Decisive WR | Net u |
|---|---|---:|---:|---:|---:|
| TRAIN | Q1 | 462 | 230/226/6 | 50.44% | -14.40 |
| TRAIN | Q2 | 462 | 219/236/7 | 48.13% | -34.52 |
| TRAIN | Q3 | 462 | 260/191/11 | 57.65% | +48.20 |
| TRAIN | Q4 | 462 | 269/187/6 | 58.99% | +60.48 |
| VALIDATION | Q1 | 127 | 68/55/4 | 55.28% | +7.56 |
| VALIDATION | Q2 | 123 | 66/54/3 | 55.00% | +6.72 |
| VALIDATION | Q3 | 124 | 62/61/1 | 50.41% | -3.96 |
| VALIDATION | Q4 | 130 | 74/52/4 | 58.73% | +16.08 |
| TEST | Q1 | 120 | 72/46/2 | 61.02% | +20.24 |
| TEST | Q2 | 159 | 86/73/0 | 54.09% | +6.12 |
| TEST | Q3 | 129 | 73/54/2 | 57.48% | +13.16 |
| TEST | Q4 | 113 | 63/48/2 | 56.76% | +9.96 |

The direction of the relationship changes between periods. In particular, TEST's best quartile is Q1, not the TRAIN-selected upper quartiles.

### Candle body / ATR
TRAIN quartile boundaries: 0.645 / 0.971 / 1.386 ATR.
| Period | Bin | n | W/L/D | Decisive WR | Net u |
|---|---|---:|---:|---:|---:|
| TRAIN | Q1 | 462 | 235/214/13 | 52.34% | +2.20 |
| TRAIN | Q2 | 462 | 242/214/6 | 53.07% | +8.64 |
| TRAIN | Q3 | 462 | 236/222/4 | 51.53% | -4.88 |
| TRAIN | Q4 | 462 | 265/190/7 | 58.24% | +53.80 |
| VALIDATION | Q1 | 118 | 64/52/2 | 55.17% | +6.88 |
| VALIDATION | Q2 | 129 | 68/55/6 | 55.28% | +7.56 |
| VALIDATION | Q3 | 138 | 71/66/1 | 51.82% | -0.68 |
| VALIDATION | Q4 | 119 | 67/49/3 | 57.76% | +12.64 |
| TEST | Q1 | 154 | 93/60/1 | 60.78% | +25.56 |
| TEST | Q2 | 142 | 82/58/2 | 58.57% | +17.44 |
| TEST | Q3 | 103 | 56/46/1 | 54.90% | +5.52 |
| TEST | Q4 | 122 | 63/57/2 | 52.50% | +0.96 |

Large bodies look relatively strong in TRAIN and VALIDATION but weakest in TEST. This argues against a simple “strong breakout candle should be faded” filter.

## Frozen-threshold check
For illustration, apply TRAIN-derived thresholds without refitting:
| Rule | Period | n | W/L/D | Decisive WR | Net u |
|---|---|---:|---:|---:|---:|
| No filter | TRAIN | 1,848 | 978/840/30 | 53.80% | +59.76 |
| No filter | VALIDATION | 504 | 270/222/12 | 54.88% | +26.40 |
| No filter | TEST | 521 | 294/221/6 | 57.09% | +49.48 |
| excess/ATR >= TRAIN median (0.3516) | TRAIN | 924 | 529/378/17 | 58.32% | +108.68 |
| same | VALIDATION | 254 | 136/113/5 | 54.62% | +12.12 |
| same | TEST | 242 | 136/102/4 | 57.14% | +23.12 |
| excess >= TRAIN Q3 boundary (2.20 pips) | TRAIN | 469 | 286/178/5 | 61.64% | +85.12 |
| same | VALIDATION | 110 | 57/50/3 | 53.27% | +2.44 |
| same | TEST | 91 | 52/37/2 | 58.43% | +10.84 |
| body/ATR >= TRAIN Q3 boundary (1.386) | TRAIN | 462 | 265/190/7 | 58.24% | +53.80 |
| same | VALIDATION | 119 | 67/49/3 | 57.76% | +12.64 |
| same | TEST | 122 | 63/57/2 | 52.50% | +0.96 |

The normalized-overshoot filter barely changes TEST decisive WR (57.09% → 57.14%) while halving trade count. The 2.20-pip overshoot filter is slightly higher on TEST (58.43%) but only 91 trades and nearly flat validation net (+2.44u). The large-body filter degrades TEST. None establishes a robust improvement.

## Conclusion
1. There is no stable monotonic relation between breakout overshoot strength and subsequent inverse success across all three chronological periods.
2. The most visually compelling TRAIN result (large overshoot/body) weakens or changes shape in VALIDATION/TEST. This is a classic overfitting warning.
3. A filter based on overshoot/ATR does not materially improve TEST win rate over the unfiltered candidate.
4. This audit does not prove the inverse edge is absent; it shows that these simple candle-shape features do not explain it reliably.
5. Do not add any of these filters to HydraAI and do not deploy the candidate on real funds. The next meaningful step is prospective, non-OTC demo observation with exact Pocket Option quotes, actual payout, timestamps, latency and all eligible/skipped signals recorded.

Research only. No production code or trading settings were changed.