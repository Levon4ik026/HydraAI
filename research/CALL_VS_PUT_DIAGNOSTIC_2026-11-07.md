# CALL vs PUT diagnostic — M5 BB + Williams %R + ADX

Date: 2026-11-07  
Branch: `hydra/stabilization`  
Dataset: `eurusd_history_extended.csv`, 30,048 M1 rows, 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC.  
Payout: **92% only** (+0.92 win / -1 loss / 0 draw).

## Scope and method

The previously frozen rule was not changed:
- M5 UTC-aligned complete candles; gaps split indicator segments.
- BB(20, 2 population SD), Williams %R(14), Wilder ADX(14).
- CALL: close re-enters above lower BB while %R crosses upward through -80.
- PUT: close re-enters below upper BB while %R crosses downward through -20.
- ADX thresholds 15, 20, 25.
- Signal after candle close; enter next M5 open; settle at that entry candle close.
- One shared non-overlapping scheduler; full history scheduled once, trades partitioned by settlement time.
- Weekly grouping uses Monday 00:00 UTC of the signal candle.

This is a diagnostic expansion of the existing short October sample, not a new independent dataset. The chronological 70/30 boundary remains 2026-10-21 19:05 UTC.

## Main finding: CALL is consistently higher in this sample, but not statistically established

At ADX >= 15 across the complete sample:

| Direction | Trades | Wins | Losses | Draws | Decisive win rate | Net at 92% |
|---|---:|---:|---:|---:|---:|---:|
| CALL | 86 | 52 | 31 | 3 | 62.65% | +16.84 |
| PUT | 59 | 27 | 29 | 3 | 48.21% | -4.16 |

The raw directional difference is 14.44 percentage points. However, the two-sided Fisher exact test gives **p = 0.1164**. This does not meet the conventional 0.05 threshold. The 95% Wilson intervals are also wide and overlap: CALL 51.90–72.28%, PUT 35.67–60.99%.

The direction gap is visible on both sides of the chronological split, but neither split independently proves it:

| Period | CALL | PUT | Fisher p |
|---|---:|---:|---:|
| Train | 56.86% (29/51) | 47.50% (19/40) | 0.4043 |
| Holdout | 71.88% (23/32) | 50.00% (8/16) | 0.2014 |

The holdout advantage is especially uncertain: only 32 CALL and 16 PUT decisive trades.

## All calendar weeks, ADX >= 15

| Signal week (UTC) | CALL | PUT | CALL minus PUT |
|---|---:|---:|---:|
| 2026-10-05 | 56.25% (9/16) | 40.00% (4/10) | +16.25 pp |
| 2026-10-12 | 53.85% (14/26) | 50.00% (12/24) | +3.85 pp |
| 2026-10-19 | 73.08% (19/26) | 52.94% (9/17) | +20.14 pp |
| 2026-10-26 | 66.67% (10/15) | 40.00% (2/5) | +26.67 pp |

CALL has a higher observed win rate in all four calendar-week buckets. But these are only four small, unequal samples, especially the final week's five PUT trades. A simple two-sided sign test for four positive weekly differences is p = 0.125; the weekly consistency is suggestive, not conclusive.

Weekly net results at 92% also show that the first two weeks were essentially flat/negative overall, while most positive performance came from the week beginning 2026-10-19. That week is part of the holdout. This leaves a material possibility of regime concentration rather than a durable directional property.

## Why the raw CALL rate may be higher

A useful baseline diagnostic was added: among all continuous adjacent M5 candles in this sample, excluding flat candles, **55.89% closed UP and 44.11% closed DOWN**. The sample itself therefore had a clear bullish candle-color skew.

Against that descriptive baseline:
- CALL: 62.65%, about **+6.76 pp** over the unconditional UP-candle rate.
- PUT: 48.21%, about **+4.10 pp** over the unconditional DOWN-candle rate.

So the CALL-vs-PUT raw win-rate gap is partly consistent with the underlying sample's bullish drift. It is not correct to interpret the full 14.44 pp difference as a pure CALL signal advantage. Both directions are above their corresponding unconditional candle-color baseline, and CALL's apparent incremental lift is only about 2.7 pp larger in this rough comparison.

The baseline is descriptive, not a formal matched control: it includes overlapping adjacent candles and is not conditioned on the exact signal timestamps, volatility, session, or ADX regime.

There is also a directional trigger imbalance before ADX filtering and scheduling: 95 raw CALL triggers versus 61 raw PUT triggers. This may reflect the sample's price path and the frequency of lower-band/oversold versus upper-band/overbought re-entries.

A plausible market-structure explanation is that during a bullish or upward-drifting regime, pullbacks toward the lower Bollinger band can be bought and rebound, while upper-band pullbacks used for PUT may be followed by renewed upward continuation. This is a hypothesis, not yet demonstrated by the current calculations.

## Threshold cross-check

| ADX minimum | CALL full-sample WR | PUT full-sample WR | Fisher p |
|---:|---:|---:|---:|
| 15 | 62.65% (52/83) | 48.21% (27/56) | 0.1164 |
| 20 | 61.76% (42/68) | 42.22% (19/45) | 0.0541 |
| 25 | 58.14% (25/43) | 42.86% (12/28) | 0.2330 |

The ADX >= 20 result is close to 0.05, but it is not below 0.05, and the three thresholds are correlated tests on the same data. It must not be promoted as statistical confirmation or used to select a threshold from this sample.

## Conclusion

**Current classification: a repeated CALL-favoring observation in this October sample, but not yet a proven persistent market effect.** Four weekly buckets point in the same direction, and the train/holdout estimates both favor CALL. However, the sample is only about three weeks of EUR/USD M1 history, the weekly sample sizes are small, the baseline is bullish, and the exact CALL-vs-PUT tests are not statistically significant.

Do not remove PUT or make CALL-only a production rule based on this result. No Desktop/GUI or live-trading behavior was changed.

## Next controlled research steps

1. Add directional DMI (+DI/-DI) and prior M5 momentum context at each signal; test whether CALL wins cluster when +DI dominates or recent momentum is positive, and whether PUT loses in the same regime.
2. Compare CALL and PUT against matched baseline candles from the same week, hour/session, and ADX bucket, avoiding overlapping controls where possible.
3. Repeat the frozen rule on a longer independent history and report month-by-month directional performance. Keep 92% payout fixed.
4. Predefine any regime filter using train data only, freeze it, then evaluate once on untouched holdout. Do not tune on the current holdout.

## Reproducibility

The expanded script prints train, holdout, full-sample, and every-week CALL/PUT breakdowns for ADX 15/20/25, Fisher exact p-values, and a descriptive next-candle baseline. The frozen holdout verification still passes.

GitHub Actions run: [run #13](https://github.com/Levon4ik026/HydraAI/actions/runs/42369674782) — success.  
Script: [reproduce_m5_bb_williams_adx.py](https://github.com/Levon4ik026/HydraAI/blob/hydra/stabilization/research/reproduce_m5_bb_williams_adx.py).
