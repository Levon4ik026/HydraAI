# HydraAI — PUT edge decay diagnostic (2026-11-07)

Branch: `hydra/stabilization`  
Payout: **92% only** (+0.92 / -1.00 / 0).  
Scope: diagnostic analysis of the previously saved broad-screen M5 PUT holdout trade log. Research only; no Desktop or production-core changes.

## Newly recovered source material

The user's Library contains the raw OHLC dataset and the saved directional screening outputs that were not committed to the repository:
- `eurusd_research_clean.csv`: 486,488 M1 rows, 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC.
  SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.
- `hydra_m5_put_holdout_trades.csv`: 376 holdout PUT trade records, June 17 through November 5, 2026.
  SHA-256: `29413862b1019668174c4a4eb70073870aa6c5facef929926b21395c3f569f25`.
- `hydra_indicator_screening_directions.csv` and `hydra_indicator_screening_summary.csv`.

The trade log's `time` field labels the final M1 minute of the five-minute entry candle. All 376 saved PnL values match the direction of that corresponding UTC-aligned M5 candle aggregated from the raw M1 dataset. This verifies outcome/time alignment for the saved holdout log.

For signal-context diagnostics, features were taken from the immediately preceding M5 candle (the signal candle). 374 of 376 trades had a continuous preceding candle available; two were excluded from feature-only slices.

## Holdout result at 92%

- 376 trades total: 197 wins, 169 losses, 10 draws.
- Decisive-trade WR: **53.83%** (197/366).
- Net: **+12.24 units**.
- 95% Wilson interval: **48.70%–58.87%**.
- Break-even WR: **52.0833%**.
- One-sided binomial test against break-even: p = **0.270**.

The point estimate is positive, but the confidence interval includes below-break-even performance and the observed result is not statistically distinguishable from the 92%-payout break-even rate.

## The edge fades after July

| Month | Trades | Wins | Losses | Draws | Decisive WR | Net | Same-month background next-M5 DOWN rate | Strategy lift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Jun 2026 | 42 | 24 | 17 | 1 | 58.54% | +5.08 | 50.53% | +8.01 pp |
| Jul 2026 | 84 | 49 | 33 | 2 | 59.76% | +12.08 | 50.34% | +9.42 pp |
| Aug 2026 | 80 | 39 | 37 | 4 | 51.32% | -1.12 | 49.93% | +1.38 pp |
| Sep 2026 | 80 | 41 | 38 | 1 | 51.90% | -0.28 | 51.44% | +0.46 pp |
| Oct 2026 | 75 | 38 | 35 | 2 | 52.05% | -0.04 | 50.82% | +1.24 pp |
| Nov 2026* | 15 | 6 | 9 | 0 | 40.00% | -3.48 | 49.12% | -9.12 pp |

*November is only a partial month through November 5.

The important observation is not simply that the market's background DOWN rate changed: it remained around 50–51%. The strategy's incremental lift over that same-month background fell from about +8–9 percentage points in June/July to roughly +0.5–1.4 points in August–October, then negative in the small November sample.

Combining June–July gives 73/123 decisive wins (59.35%, +17.16 units). August–October gives 118/228 (51.75%, -1.44 units). The 7.60 pp difference is suggestive but not conclusive (two-sided Fisher exact p = 0.180). These are not independent market observations, and the split was identified after inspecting the time series.

## Basic signal-time regime mix does not explain the decay

The broad saved trade log is heavily concentrated in bullish-DMI / positive-short-momentum contexts, and that composition was fairly stable through the main months:

| Month | +DI dominant | Prior M3 momentum UP | ADX >=20 |
|---|---:|---:|---:|
| Jun | 97.62% | 88.10% | 33.33% |
| Jul | 98.81% | 95.24% | 46.43% |
| Aug | 98.75% | 88.75% | 42.50% |
| Sep | 97.50% | 93.75% | 55.00% |
| Oct | 100.00% | 90.67% | 41.33% |

This makes a simple explanation such as “the strategy stopped working because it began trading a different DMI or M3 momentum regime” unlikely. It does not rule out more granular effects involving volatility, session, trend maturity, or event conditions.

## Time-of-day is a research lead, not a filter

Exploratory UTC-hour buckets in the saved holdout log:

| Signal-time UTC | Trades | Decisive WR | Background DOWN rate | Lift | Net |
|---|---:|---:|---:|---:|---:|
| 00–05 | 108 | 50.49% | 50.04% | +0.45 pp | -3.16 |
| 06–09 | 80 | 44.30% | 49.79% | -5.49 pp | -11.80 |
| 10–13 | 52 | 54.90% | 50.79% | +4.11 pp | +2.76 |
| 14–17 | 60 | 55.17% | 50.58% | +4.59 pp | +3.44 |
| 18–21 | 53 | 64.15% | 50.40% | +13.76 pp | +12.28 |
| 22–23 | 23 | 72.73% | 48.46% | +24.27 pp | +8.72 |

Evening buckets look promising, while 06–09 UTC is notably weak. However, the last two buckets contain only 53 and 23 trades, respectively; the hour boundaries were inspected post hoc and many comparisons are possible. **No session filter is approved.** This needs a pre-registered test on a fresh later period.

## Important reproducibility limitation

The saved broad-screen report describes “M5 Bollinger re-entry + Williams %R + ADX,” but the exact original broad-screen implementation is not present in the repository. The current stabilization-branch reproduction script uses an explicit BB20 / 2 population-SD, Williams %R14, Wilder ADX14 rule. Applying that exact current rule to the recovered history does **not** reproduce the 376 saved PUT signal timestamps: only 163/376 saved trades satisfy the current implementation's strict upper-band/Williams re-entry condition when signal-time features are mapped from the raw file. Therefore the saved trade log's outcomes can be checked against OHLC, but its original signal-selection logic is not yet independently reproduced.

This distinction matters: do not treat the October short-sample screen as an exact reproduction of the broad June–November PUT strategy. They are separate experiments until the original rule is recovered.

## Current conclusions

1. The old broad PUT result was front-loaded: most of its positive net came from June and July.
2. After July, its measured incremental lift over same-month background candle direction was close to zero.
3. Simple DMI/M3/ADX composition does not explain the deterioration.
4. UTC session timing is a plausible hypothesis, but it is post-hoc and underpowered.
5. The 376-trade aggregate result is not statistically established above 92%-payout break-even.
6. No PUT strategy or time filter is ready for production, and CALL remains frozen as a separate research control.

## Next research steps

- Recover the exact original broad-screen rule and indicator conventions before claiming exact reproduction.
- Build a pre-registered session/volatility/regime hypothesis, fit only on earlier data, then evaluate once on an untouched later chronological segment.
- Search for alternative PUT-specific mechanisms on the full 486,488-row history, not only the three-week October subset.
- Keep payout fixed at 92%; preserve non-overlap, gap handling, and next-candle entry/settlement rules.
- Test the eventual CALL + PUT pair under one shared scheduler and WAIT/conflict policy only after each side has independent evidence.

No Desktop code, live strategy, or automatic trading was changed.
