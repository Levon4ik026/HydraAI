# Post-breakout failure audit — inverse MOM_BREAK_24 (2026-11-09)

## Research question
After a bullish close above the previous 24 M5 highs, does the next one or two M5 candles show a failed continuation that improves the inverse PUT entry?

## Data and construction
- Source: `eurusd_research_clean.csv`, 486,488 valid EUR/USD M1 BID rows.
- Complete UTC-aligned M5 bars: 97,227 across 68 gap-separated segments.
- Base event: completed M5 candle closes above the highest high of the previous 24 M5 candles and is bullish.
- Post-breakout observation is made only after the next one or two completed M5 candles. Entry is at the open of the M5 candle immediately after the observation candle; thus no future data is used for entry.
- Inverse side: PUT. Expiry is close of the 1st/2nd/3rd/4th M5 candle after entry (5/10/15/20 minutes).
- A one-position schedule is enforced per rule and continuity segment; a new event is eligible once the prior expiry candle has closed.
- Chronological boundaries: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06. Events settling across a split boundary are purged.
- Fixed payout illustration: WIN +0.92u, LOSS -1u, DRAW 0u; break-even decisive WR 52.0833%.
- All results are historical Dukascopy BID candles, not Pocket Option executable quotes or actual payout history.

## Definitions
- `delay1_all`: observe the first candle after the breakout; enter next candle regardless of its shape.
- `delay1_closeback`: first post-breakout candle closes at or below the broken 24-bar high (returns inside the old range).
- `delay1_closeback_bear`: closeback plus bearish post-breakout candle.
- `delay1_closeback_failedhigh`: closeback plus post-breakout high does not exceed the breakout candle high.
- `delay1_all3`: closeback + bearish + failed-high conditions.
- `delay1_wick40`: closeback plus upper wick at least 40% of candle range.
- `delay2_all`: wait through two completed post-breakout candles, then enter next candle.
- `delay2_closeback_bear`: at the second post-breakout candle, close is back inside the prior range and candle is bearish.

## Results: 15-minute expiry
| Rule | Period | Trades | W/L/D | Decisive WR | Net units |
|---|---|---:|---:|---:|---:|
| delay1_all | TRAIN | 2,090 | 1,110/949/31 | 53.91% | +72.20 |
| delay1_all | VALIDATION | 565 | 296/263/6 | 52.95% | +9.32 |
| delay1_all | TEST | 597 | 324/263/10 | 55.20% | +35.08 |
| delay1_closeback | TRAIN | 987 | 489/481/17 | 50.41% | -31.12 |
| delay1_closeback | VALIDATION | 243 | 128/110/5 | 53.78% | +7.76 |
| delay1_closeback | TEST | 251 | 144/103/4 | 58.30% | +29.48 |
| delay1_closeback_bear | TRAIN | 987 | 489/481/17 | 50.41% | -31.12 |
| delay1_closeback_bear | VALIDATION | 243 | 128/110/5 | 53.78% | +7.76 |
| delay1_closeback_bear | TEST | 250 | 144/102/4 | 58.54% | +30.48 |
| delay1_closeback_failedhigh | TRAIN | 569 | 274/284/11 | 49.10% | -31.92 |
| delay1_closeback_failedhigh | VALIDATION | 142 | 74/65/3 | 53.24% | +3.08 |
| delay1_closeback_failedhigh | TEST | 154 | 86/66/2 | 56.58% | +13.12 |
| delay1_wick40 | TRAIN | 141 | 78/61/2 | 56.12% | +10.76 |
| delay1_wick40 | VALIDATION | 45 | 18/26/1 | 40.91% | -9.44 |
| delay1_wick40 | TEST | 35 | 21/14/0 | 60.00% | +5.32 |
| delay2_all | TRAIN | 2,090 | 1,060/1,001/29 | 51.43% | -25.80 |
| delay2_all | VALIDATION | 565 | 297/260/8 | 53.32% | +13.24 |
| delay2_all | TEST | 597 | 319/273/5 | 53.89% | +20.48 |
| delay2_closeback_bear | TRAIN | 869 | 418/434/17 | 49.06% | -49.44 |
| delay2_closeback_bear | VALIDATION | 216 | 107/105/4 | 50.47% | -6.56 |
| delay2_closeback_bear | TEST | 234 | 128/100/6 | 56.14% | +17.76 |

## Results: 20-minute expiry
| Rule | Period | Trades | W/L/D | Decisive WR | Net units |
|---|---|---:|---:|---:|---:|
| delay1_all | TRAIN | 1,886 | 1,011/850/25 | 54.33% | +80.12 |
| delay1_all | VALIDATION | 514 | 270/233/11 | 53.68% | +15.40 |
| delay1_all | TEST | 537 | 281/248/8 | 53.12% | +10.52 |
| delay1_closeback | TRAIN | 951 | 471/466/14 | 50.27% | -32.68 |
| delay1_closeback | VALIDATION | 236 | 130/105/1 | 55.32% | +14.60 |
| delay1_closeback | TEST | 243 | 132/106/5 | 55.46% | +15.44 |
| delay1_closeback_failedhigh | TRAIN | 560 | 264/286/10 | 48.00% | -43.12 |
| delay1_closeback_failedhigh | VALIDATION | 142 | 79/62/1 | 56.03% | +10.68 |
| delay1_closeback_failedhigh | TEST | 152 | 78/69/5 | 53.06% | +2.76 |
| delay1_wick40 | TRAIN | 139 | 81/58/0 | 58.27% | +16.52 |
| delay1_wick40 | VALIDATION | 45 | 19/26/0 | 42.22% | -8.52 |
| delay1_wick40 | TEST | 35 | 20/15/0 | 57.14% | +3.40 |
| delay2_all | TRAIN | 1,886 | 1,003/863/20 | 53.75% | +59.76 |
| delay2_all | VALIDATION | 514 | 277/232/5 | 54.42% | +22.84 |
| delay2_all | TEST | 537 | 277/253/7 | 52.26% | +1.84 |
| delay2_closeback_bear | TRAIN | 860 | 417/433/10 | 49.06% | -49.36 |
| delay2_closeback_bear | VALIDATION | 215 | 109/104/2 | 51.17% | -3.72 |
| delay2_closeback_bear | TEST | 233 | 127/103/3 | 55.22% | +13.84 |

## Other horizons: key observations
At 5/10/15/20 minutes, the first-candle closeback rule produced:
- TRAIN: 52.65% / 49.29% / 50.41% / 50.27%.
- VALIDATION: 47.95% / 53.28% / 53.78% / 55.32%.
- TEST: 50.59% / 55.51% / 58.30% / 55.46%.

For comparison, waiting one candle but entering regardless of its shape (`delay1_all`) produced:
- TRAIN: 52.77% / 53.09% / 53.91% / 54.33%.
- VALIDATION: 50.12% / 52.46% / 52.95% / 53.68%.
- TEST: 51.77% / 53.98% / 55.20% / 53.12%.

Thus, closeback appears to add some TEST lift at 10–20m versus the delayed-entry baseline, but it is materially negative in TRAIN and weaker than baseline in TRAIN. This is not a stable cross-period improvement.

## Interpretation
1. The simple idea “breakout closes back inside the prior range on the next candle” is interesting on the most recent TEST segment at 10–20m, particularly 15m (58.30%, +29.48u, 251 trades).
2. The same closeback rule loses in TRAIN at all tested horizons; therefore the apparent TEST lift is regime-dependent, not a robust general rule.
3. Adding “no new high beyond the breakout candle” reduces sample size and does not improve the 15m TEST result versus closeback alone.
4. The 40% upper-wick condition has only 35 TEST trades and is strongly negative in VALIDATION. Its attractive TEST percentage is a small-sample trap.
5. Waiting two candles does not give a stable advantage; the bearish-closeback version is negative in TRAIN and VALIDATION.
6. The best-looking rule/horizon was selected from multiple exploratory comparisons. No multiple-testing correction has been applied, and the same historical dataset has already been explored.
7. No production HydraAI code was changed; no live or demo trades were executed.

## Next required validation
Freeze one hypothesis only if it survives a pre-declared rule and test it prospectively on fresh non-OTC Pocket Option demo observations. Log every eligible breakout, confirmation, skipped event, exact platform entry/settlement quotes, actual payout, and latency. Until then, this remains research-only and must not be promoted to a live signal.
