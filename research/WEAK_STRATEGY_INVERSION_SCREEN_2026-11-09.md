# Weak-strategy inversion screen — 2026-11-09

## Objective
Screen pre-specified weak directional patterns from the repository's standalone EUR/USD M5 strategy family and test the exact opposite direction on the identical entries and expiries. Research only; no HydraAI production or execution changes.

## Data and replay protocol
- Input: `eurusd_research_clean.csv`, 486,488 EUR/USD M1 candles, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.
- Complete UTC-aligned M5 candles: 97,227; continuity segments: 68. Incomplete M5 buckets are excluded; no signal lookback or expiry crosses a gap.
- Calendar-date split: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06 onward.
- Signal uses only the completed M5 candle. Entry = next M5 open. Expiry = close of the Nth subsequent M5 candle: 5, 10, 15, 20, 30 or 60 minutes.
- Families: false range break, momentum range break, mean reversion, engulfing, rejection pin bar; 20 directional/parameter variants and six horizons.
- One-position schedule enforced separately per strategy, expiry and continuity segment. A signal is accepted only after the previous trade of that same strategy/expiry has expired. Different strategies can overlap; these results are not a combined portfolio.
- A CALL is inverted to PUT and PUT to CALL without changing signal timestamp, entry, expiry or sample. Ties remain ties. Thus inverse W/L counts swap exactly.
- Payout assumption: fixed 92% net payout, +0.92 per win / -1 per loss / 0 draw. Break-even decisive win rate = 52.0833%.
- Feed is historical EUR/USD candle data, not Pocket Option's exact executable quote stream. Platform payout variation, quote differences, spread, latency and settlement mechanics are not modelled.

## Main finding
**Yes: several weak rules become better when inverted.** One especially interesting candidate is a momentum range-break CALL rule: close above the highest high of the previous 24 M5 candles, with a bullish signal candle. Its exact inverse sells PUT at the same next-bar entry and settles at the same expiry.

### Best balanced lead: MOM_BREAK_24_CALL, inverted, 20-minute expiry
| Period | Trades | Inverse wins | Inverse losses | Draws | Inverse WR | Net at 92% |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,886 | 993 | 862 | 31 | 53.53% | +51.56u |
| VALIDATION | 515 | 277 | 226 | 12 | 55.07% | +28.84u |
| TEST | 537 | 298 | 232 | 7 | 56.23% | +42.16u |

The direct rule's corresponding decisive win rates were 46.47%, 44.93%, and 43.77%. Direct and inverse rates sum to 100% in every period. The inverse had positive theoretical net in all three chronological periods. However, Wilson 95% intervals for the inverse are wide: TRAIN 51.26–55.79%, VALIDATION 50.70–59.36%, TEST 51.97–60.39%. The simple one-sided binomial p-values against 52.0833% are 0.110, 0.097 and 0.031 respectively. These p-values are unadjusted for multiple strategy/horizon searches and serial dependence; they are not confirmatory evidence.

### Other candidate leads
| Original weak rule | Expiry | Inverse TRAIN WR | Inverse VALIDATION WR | Inverse TEST WR | TEST net @92% |
|---|---:|---:|---:|---:|---:|
| MOM_BREAK_12_CALL | 20m | 54.44% | 52.61% | 57.40% | +78.64u |
| MOM_BREAK_24_CALL | 15m | 54.74% | 53.93% | 55.65% | +40.60u |
| PIN_REJECT_CALL | 5m | 50.60% | 53.08% | 54.38% | +58.40u |
| PIN_REJECT_CALL | 10m | 50.09% | 52.63% | 53.99% | +45.92u |
| MOM_BREAK_24_CALL | 30m | 54.06% | 55.82% | 53.03% | +8.40u |

These are leads from a 20-variant × 6-expiry screen, not independently confirmed strategies. Selection among many combinations makes the best TEST row optimistically biased.

### Important caution: stability is not uniform
For MOM_BREAK_12_CALL inverted at 20m, the validation period was only 52.61% (383 wins / 345 losses, 13 draws; +7.36u), while test rose to 57.40% (442 / 328, 11 draws; +78.64u). Monthly TEST results weakened over time: 61.57% in Aug 2026, 59.09% in Sep, 53.67% in Oct and 50.94% in the partial Nov sample. This may indicate a regime effect or decaying edge.
For MOM_BREAK_24_CALL inverted at 20m, the chronological results are more even, but its validation confidence interval still includes break-even.

## Exact reversal sanity check
For every accepted trade in this screen, direct and inverse outcomes were computed from the same entry and exit prices. Inversion swaps WIN and LOSS; DRAW remains DRAW. Therefore:
- direct wins = inverse losses;
- direct losses = inverse wins;
- direct decisive WR + inverse decisive WR = 100%;
- the net at 92% is recomputed separately as 0.92 × wins − losses.

No result was obtained by comparing unrelated samples or changing entry/expiry.

## Decision
1. **Do not deploy yet.** The screen does identify genuine weak-rule/inverse candidates, but it is a multi-comparison historical discovery exercise.
2. First candidate for deeper validation: `MOM_BREAK_24_CALL` inverted, 20-minute expiry. It has a less dramatic but more even train/validation/test profile than the highest TEST performer.
3. Second candidate: `MOM_BREAK_12_CALL` inverted, 20-minute expiry. Its TEST is stronger, but validation is close to break-even and later monthly results decline.
4. Re-run both with a pre-registered frozen rule on a new, untouched forward period using the actual Pocket Option non-OTC feed and observed payout per trade. Report monthly W/L/D, net, drawdown, losing streak and time-clustered uncertainty.
5. Keep auto-trading disabled and do not add either rule to HydraAI signals until the prospective test passes.

## Rule definitions
- `MOM_BREAK_12_CALL`: signal CALL when current M5 close exceeds the highest high of the previous 12 M5 bars and current candle is bullish.
- `MOM_BREAK_24_CALL`: same, using the previous 24 M5 bars.
- `PIN_REJECT_CALL`: signal CALL when lower wick is at least 60% of candle range and close is in the upper 35% of the range.
- Inversion means replacing each CALL by PUT, preserving the same event and expiry.

## Reproducibility note
This report records a vectorized replay of the standalone strategy-family definitions in `research/standalone_strategy_screen.py` on the clean M1 history. It is not a new Pocket Option execution test. The exact dataset and split dates are stated above so the screen can be independently reproduced and extended.
