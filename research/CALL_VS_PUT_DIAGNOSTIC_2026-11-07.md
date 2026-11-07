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


## Second-stage diagnostic: DMI, momentum, and context-adjusted baseline

Added Wilder +DI/-DI components from the same ADX(14) calculation, plus prior 3- and 6-candle M5 close-to-close momentum. These values are measured at the signal candle close, so no future information enters the regime label. The strategy entry/settlement scheduler and frozen rules are unchanged.

### Important structural finding

The signal directions are strongly associated with opposite DMI states:
- 82 of 86 CALL trades occurred with -DI > +DI.
- 55 of 59 PUT trades occurred with +DI > -DI.

This is expected to some extent for a mean-reversion rule: CALLs trigger near the lower Bollinger band after downward pressure; PUTs trigger near the upper band after upward pressure. It means a simple comparison of CALL and PUT inside the same DMI bucket is not a balanced experiment: there are very few CALLs in +DI-dominant states and very few PUTs in -DI-dominant states.

### Directional results by momentum state

For ADX >= 15, full-sample M3 momentum:
- M3 momentum DOWN: CALL 63.93% (39/61 decisive), PUT 43.48% (10/23).
- M3 momentum UP: CALL 59.09% (13/22), PUT 53.12% (17/32).
- In the untouched holdout, M3 DOWN: CALL 68.00% (17/25), PUT 28.57% (2/7); M3 UP: CALL 85.71% (6/7), PUT 75.00% (6/8).

These splits are descriptive only. The holdout groups are tiny, and none supplies reliable proof of a directional interaction. The full-sample M6-UP split showed CALL 90% (9/10) versus PUT 51.02% (25/49), Fisher p=0.0338, but this result does not persist in holdout (CALL 80% of 5; PUT 53.85% of 13; p=0.596). Treat the M6 result as a likely small-sample/multiple-testing artifact, not a filter.

### Context-adjusted baseline

For every eligible M5 candle with ADX >= 15, the diagnostic estimates the next candle's UP/DOWN rate within its signal-time DMI x M3-momentum bucket. Each strategy trade is then compared with the corresponding same-context background probability (UP for CALL, DOWN for PUT). This is a descriptive, overlapping-candle benchmark, not a causal matched-control study; it can still be affected by serial dependence and the limited date range.

| Period | Direction | Observed strategy WR | Same-context background WR | Lift |
|---|---|---:|---:|---:|
| Full | CALL | 62.65% | 59.20% | +3.45 pp |
| Full | PUT | 48.21% | 46.82% | +1.39 pp |
| Train | CALL | 56.86% | 58.85% | -1.98 pp |
| Train | PUT | 47.50% | 46.47% | +1.03 pp |
| Holdout | CALL | 71.88% | 60.40% | +11.47 pp |
| Holdout | PUT | 50.00% | 47.53% | +2.47 pp |

This materially changes the interpretation. Across the full sample, the raw CALL-versus-PUT WR gap is 14.44 pp, but the same-context background rates already differ by about 12.38 pp (59.20% CALL-side UP baseline versus 46.82% PUT-side DOWN baseline). After this coarse context adjustment, the strategy's residual lifts are only +3.45 pp CALL and +1.39 pp PUT. Most of the apparent CALL/PUT gap is therefore consistent with the different market states in which the two kinds of mean-reversion signals occur, rather than a demonstrated intrinsic superiority of CALL.

### Week-by-week context-adjusted lift

| Signal week UTC | CALL lift vs context baseline | PUT lift vs context baseline |
|---|---:|---:|
| 2026-10-05 | -0.75 pp (n=16) | -4.37 pp (n=10) |
| 2026-10-12 | -6.81 pp (n=26) | +2.94 pp (n=24) |
| 2026-10-19 | +9.66 pp (n=26) | +5.16 pp (n=17) |
| 2026-10-26 | +16.54 pp (n=15) | -10.25 pp (n=5) |

CALL's incremental lift is not consistent across weeks: it was negative in the first two weeks, then positive in the last two. The strong last two weeks coincide with the prior holdout. PUT is also mixed. This pattern is more consistent with a change in market conditions during the holdout than with a stable, always-present CALL advantage. The last week's PUT estimate is especially noisy (five decisive trades).

### Revised verdict

**We have not established that CALL is intrinsically better than PUT.** The unadjusted CALL win rate is higher, but the signal types occur in substantially different DMI/momentum states, and the broad background next-candle rates already explain most of the observed gap. After coarse context adjustment, the full-sample incremental lift is small for both directions; CALL's lift appears concentrated in the last two weeks and is negative in the training period.

Do not disable PUT, enable CALL-only, or encode a directional preference in the Desktop. The next valid test is a longer independent EUR/USD M1 history with a pre-registered, frozen regime adjustment and non-overlapping, signal-time matched controls. Use the same 92% payout and report each month separately. Any proposed DMI/momentum filter must be specified using train data only and evaluated once on a genuinely untouched later period.

## Reproducibility update

- Added +DI/-DI and 3-/6-bar momentum features to the research script.
- Added full/train/holdout regime splits and week-by-week context-adjusted baselines.
- Added a unit test for DMI component calculation.
- Latest GitHub Actions run #18: success — [run #18](https://github.com/Levon4ik026/HydraAI/actions/runs/42370418521).
- Latest script: [reproduce_m5_bb_williams_adx.py](https://github.com/Levon4ik026/HydraAI/blob/hydra/stabilization/research/reproduce_m5_bb_williams_adx.py).
