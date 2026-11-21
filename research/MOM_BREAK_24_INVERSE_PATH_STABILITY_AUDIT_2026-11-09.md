# MOM_BREAK_24_CALL inversion — path, time and stability audit (2026-11-09)

## Scope

This follow-up tests the previously nominated candidate: the M5 momentum range-break CALL rule inverted to PUT, with a 20-minute expiry. It uses the same clean EURUSD M1 CSV and exact strategy definitions as the corrected replay. No production code was changed and no trades were executed.

## Reproduction and candidate schedule

- M1 input: 486,488 rows, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- Complete UTC-aligned M5 bars: 97,227; 68 continuity segments.
- Signal: on a completed M5 candle, close > highest high of previous 24 M5 bars and current candle bullish.
- Inverse: PUT at the next M5 open; expiry at close of fourth subsequent M5 candle (20 minutes after entry).
- Signals are scheduled one position at a time per strategy/expiry/continuity segment. The tested 20m cohort has 2,873 accepted trades: TRAIN 1,848; VALIDATION 504; TEST 521.
- Inverse outcome is exact complement of direct CALL on identical entry/exit: direct W↔inverse L, direct L↔inverse W, draws unchanged.
- Fixed payout scenarios are theoretical only. Base case 92% net payout; break-even decisive WR 52.0833%.
- Quotes are Dukascopy BID candles, not Pocket Option executable quotes.

## 20-minute result by chronological period

| Period | Trades | Inverse W/L/D | Decisive WR | Net units at 92% |
|---|---:|---:|---:|---:|
| TRAIN | 1,848 | 978/840/30 | 53.80% | +59.76 |
| VALIDATION | 504 | 270/222/12 | 54.88% | +26.40 |
| TEST | 521 | 294/221/6 | 57.09% | +49.48 |

Wilson 95% intervals: TRAIN 51.50–56.08%; VALIDATION 50.46–59.22%; TEST 52.78–61.29%. One-sided exact binomial p-values against 52.0833%: TRAIN 0.0752; VALIDATION 0.1158; TEST 0.0128. The TEST p-value is unadjusted for the 120 strategy/horizon combinations screened and assumes independent decisive outcomes. It is not confirmatory.

TEST sequential net drawdown at 92% was 10.16 units; maximum losing streak was 7. These values depend on the exact chronological ordering and fixed payout.

A 10,000-replicate bootstrap resampling whole TEST calendar dates (66 dates; seed 20261109) gave a 95% percentile interval for total net of approximately +6.52 to +90.00 units, and for decisive WR 52.73–61.40%. This is a date-cluster resampling sensitivity check, not a fully specified time-series block bootstrap; it does not correct for candidate selection or structural regime shifts.

## Monthly stability

| Month UTC | Trades | W/L/D | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|
| 2026-08 | 171 | 103/66/2 | 60.95% | +28.76 |
| 2026-09 | 164 | 98/63/3 | 60.87% | +27.16 |
| 2026-10 | 172 | 89/82/1 | 52.05% | -0.12 |
| 2026-11* | 37 | 21/16/0 | 56.76% | +3.32 |

*November is partial (dataset ends 2026-11-05). The sharp deterioration in October is material: the edge was not consistently strong month to month. August and September are not enough to establish durability.

## Time-of-day diagnostic (UTC, fixed 6-hour buckets)

This is a descriptive UTC grouping, not a precise London/New York/Asia session classification; daylight-saving shifts are not adjusted.

| Period | UTC 00–05 | UTC 06–11 | UTC 12–17 | UTC 18–23 |
|---|---:|---:|---:|---:|
| TRAIN WR (n) | 54.47% (479) | 51.66% (518) | 55.53% (516) | 53.47% (335) |
| VALIDATION WR (n) | 52.38% (130) | 52.29% (157) | 63.36% (133) | 50.00% (84) |
| TEST WR (n) | 58.39% (164) | 54.97% (153) | 49.14% (117) | 68.97% (87) |
| ALL WR (n) | 54.95% (773) | 52.39% (828) | 55.91% (766) | 55.60% (506) |

The apparent TEST strength is concentrated in UTC 00–05 and 18–23, while UTC 12–17 is below break-even. These are post-hoc slices with small samples and multiple comparisons; do not create a session filter from them yet.

## Price path after the entry

To avoid selecting a different signal set at every horizon, this section follows the exact same 20-minute-scheduled entries and checks the inverse PUT direction at each subsequent close. The sample count remains 1,848 / 504 / 521 across periods.

| Period | Horizon | Inverse decisive WR | Net units at 92% |
|---|---:|---:|---:|
| TRAIN | 5m | 51.61% | -16.56 |
| TRAIN | 10m | 54.25% | +75.28 |
| TRAIN | 15m | 54.73% | +92.40 |
| TRAIN | 20m | 53.80% | +59.76 |
| TRAIN | 30m | 55.14% | +107.28 |
| TRAIN | 60m | 53.30% | +42.76 |
| VALIDATION | 5m | 53.11% | +9.52 |
| VALIDATION | 10m | 53.33% | +11.88 |
| VALIDATION | 15m | 54.53% | +23.32 |
| VALIDATION | 20m | 54.88% | +26.40 |
| VALIDATION | 30m | 55.51% | +32.84 |
| VALIDATION | 60m | 52.10% | +0.20 |
| TEST | 5m | 54.06% | +19.16 |
| TEST | 10m | 53.43% | +13.16 |
| TEST | 15m | 56.01% | +38.88 |
| TEST | 20m | 57.09% | +49.48 |
| TEST | 30m | 55.15% | +30.28 |
| TEST | 60m | 56.23% | +40.88 |

This same-entry path analysis suggests that the fade effect is not immediate: 5-minute results are weaker than 15–30-minute results. However, horizons are highly correlated because they reuse the same trades and prices. The best row must not be interpreted as a fresh independent test.

Mean favorable/adverse intratrade excursions for the inverse PUT over the 20-minute window (entry through expiry candle, using candle highs/lows):
- TRAIN: favorable 4.12 pips, adverse 3.77 pips.
- VALIDATION: favorable 3.44 pips, adverse 3.47 pips.
- TEST: favorable 3.31 pips, adverse 3.28 pips.

Average signed entry-to-expiry movement for the inverse PUT was small: TRAIN +0.402 pips, VALIDATION +0.152 pips, TEST +0.222 pips. These are BID candle close-to-open differences and are not Pocket Option payout units. The small price displacement reinforces the need to test exact platform quotes and payout, rather than assume a candle-based edge translates directly.

## Payout sensitivity on TEST

With 294 wins, 221 losses and 6 draws:
- 80% payout: +14.20 units (break-even WR 55.56%).
- 85% payout: +28.90 units (break-even WR 54.05%).
- 90% payout: +43.60 units (break-even WR 52.63%).
- 92% payout: +49.48 units (break-even WR 52.08%).
- 95% payout: +58.30 units (break-even WR 51.28%).

This is arithmetic sensitivity only; the dataset contains no historical per-trade Pocket Option payout.

## Findings and decision

1. The inverse has a positive historical result at 20m across all three chronological splits, but uncertainty remains broad and multiple-testing bias is substantial.
2. The apparent TEST edge is not stable by month: August and September are strong, October is effectively flat, and November is only 37 trades.
3. The effect is not strongest immediately after entry. On the same entry cohort, the 15–30m closes are generally better than 5m, but the horizons are correlated.
4. Fixed UTC time slices suggest different regimes, but the pattern is post-hoc and must not be used to add a time filter.
5. The average directional price move is small. A Pocket Option prospective test must log the actual quote used for entry and settlement, payout shown at entry, timestamp/latency, non-OTC symbol, and all eligible signals including skipped/overlapping ones.
6. Do not deploy this candidate or add it to live HydraAI signal generation yet. Next defensible experiment: freeze the 24-bar breakout definition and 20m expiry, record a prospective untouched sample, and report monthly W/L/D, actual payout-weighted net, drawdown, losing streak, and session/time slices fixed in advance.

Research only. No production files were changed; no trades were placed.
