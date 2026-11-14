# Corrected weak-strategy inversion replay — 2026-11-09

## Why this correction exists

The earlier file `WEAK_STRATEGY_INVERSION_SCREEN_2026-11-09.md` reported counts and rates that were not supported by the checked-in replay code. An audit found that `standalone_strategy_screen.py` computes direct outcomes only; it does not itself implement the claimed inversion or print the earlier report's candidate table. The earlier report therefore must not be treated as a verified replay. This document replaces its numerical claims with a fresh independent run of the strategy definitions against the named CSV.

## Reproduction

- Input: `eurusd_research_clean.csv`; 486,488 valid M1 rows.
- UTC-aligned complete M5 bars: 97,227; 68 gap-separated segments.
- Date split: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06.
- Signal definitions, loop bounds, and event scheduling follow `research/standalone_strategy_screen.py`.
- Closed M5 signal; next M5 open entry; expiry at close of the Nth subsequent M5 bar (5/10/15/20/30/60m).
- One-position schedule per strategy, expiry, and continuity segment; the next signal is eligible at the prior expiry bar's close.
- For each accepted event, inverse outcome is computed on the exact same entry/exit: W↔L, D→D. Fixed 92% payout: +0.92/-1/0 units; break-even decisive WR 52.0833%.
- This is a historical BID-candle replay, not Pocket Option's executable quote stream. Payout changes, platform quote differences, spread, latency and settlement rules are not modelled.

## Reproduced inverse candidates

All counts below are independently re-computed from the dataset and the checked-in strategy definitions. W/L/D in the table are the **inverse** outcomes; net = 0.92×W − L.

| Original rule inverted | Expiry | Period | Trades | W/L/D | Decisive WR | Net units |
|---|---:|---|---:|---:|---:|---:|
| MOM_BREAK_12_CALL | 20m | TRAIN | 2,648 | 1,427/1,184/37 | 54.65% | +128.84 |
| MOM_BREAK_12_CALL | 20m | VALIDATION | 715 | 367/335/13 | 52.28% | +2.64 |
| MOM_BREAK_12_CALL | 20m | TEST | 749 | 431/308/10 | 58.32% | +88.52 |
| MOM_BREAK_24_CALL | 20m | TRAIN | 1,848 | 978/840/30 | 53.80% | +59.76 |
| MOM_BREAK_24_CALL | 20m | VALIDATION | 504 | 270/222/12 | 54.88% | +26.40 |
| MOM_BREAK_24_CALL | 20m | TEST | 521 | 294/221/6 | 57.09% | +49.48 |
| PIN_REJECT_CALL | 5m | TRAIN | 4,744 | 2,318/2,270/156 | 50.52% | -137.44 |
| PIN_REJECT_CALL | 5m | VALIDATION | 1,347 | 689/608/50 | 53.12% | +25.88 |
| PIN_REJECT_CALL | 5m | TEST | 1,311 | 685/570/56 | 54.58% | +60.20 |
| MOM_BREAK_24_CALL | 15m | TRAIN | 2,047 | 1,106/907/34 | 54.94% | +110.52 |
| MOM_BREAK_24_CALL | 15m | VALIDATION | 553 | 291/255/7 | 53.30% | +12.72 |
| MOM_BREAK_24_CALL | 15m | TEST | 579 | 322/252/5 | 56.10% | +44.24 |

## Confidence intervals (Wilson 95%, descriptive)

- MOM_BREAK_12_CALL inverted, 20m: TRAIN 52.74–56.55%; VALIDATION 48.58–55.95%; TEST 54.73–61.82%.
- MOM_BREAK_24_CALL inverted, 20m: TRAIN 51.50–56.08%; VALIDATION 50.46–59.22%; TEST 52.78–61.29%.

These intervals do not correct for searching 20 variants × 6 horizons, and assume independent decisive outcomes. Serial dependence and shared market regimes make them optimistic as evidence of a durable edge.

## Exact complement check

For every accepted trade, direct and inverse outcomes are paired on identical prices and expiry. Thus direct W count equals inverse L count, direct L equals inverse W, and draws are unchanged. This identity is mathematical and does not imply the inverse strategy has a durable predictive edge.

## Interpretation

1. The strongest balanced candidate in this rerun is MOM_BREAK_24_CALL inverted at 20m: positive net in all three chronological slices, but its validation interval includes the 52.0833% break-even threshold.
2. MOM_BREAK_12_CALL inverted at 20m has the strongest TEST result here, but validation is only +2.64 units and its interval is broad. Do not select it based on TEST performance.
3. PIN_REJECT_CALL inverted at 5m is not stable: it loses -137.44 units in TRAIN, then is positive in later slices. This is a regime-change warning, not evidence of a robust strategy.
4. Because the historical sample has already been explored, TEST is not an untouched holdout. No strategy is approved for deployment.
5. Next valid step: freeze one candidate and evaluate prospectively on fresh non-OTC Pocket Option observations, recording actual payout, platform entry/settlement quotes, all signals including skipped ones, and drawdown.

Research only. No production HydraAI code was changed and no trades were executed.
