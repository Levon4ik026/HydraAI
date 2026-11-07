# HYDRA market stress-test protocol — November 2026

## Purpose
Evaluate whether frozen CALL and PUT rules remain reliable during abnormal EUR/USD conditions. This is research only: no order execution, OTC instruments, Desktop integration, or parameter tuning.

## Event under investigation
The user recalled a sharp US-equity selloff as having occurred "yesterday". The prior review provisionally identified Thursday 2026-11-05 as the major US-equity decline; 2026-11-07 was Saturday. This is a working event identification, not proof that EUR/USD experienced a matching shock. Confirm the exact event window and FX characteristics from timestamped EUR/USD candles before drawing conclusions.

## What has already been tested
The supplied guest-feed CSV had a continuous non-flat M1 segment on 2026-11-05 with 529 rows (12:21–21:09 UTC), producing 105 complete M5 candles without crossing a gap. The frozen PUT selector produced two signals: one loss and one win, net -0.08 units at fixed 92% payout. This was a mechanical smoke test only. Broader historical research was not explicitly designed as an event-specific stress test. No separate CALL-vs-PUT event comparison or WAIT-filter stress study has been completed.

The 2026-11-07 guest-feed audit found 605 exactly flat rows in a Saturday tail and repeated connection failures. Do not treat these rows as genuine tradable prices. Keep missing intervals as hard segment boundaries.

## Required study design
1. Confirm the equity-event date/time independently, then inspect synchronized EUR/USD M1 candles. Do not infer FX volatility from equity index returns.
2. Define the event window before inspecting strategy outcomes. Report pre-event, event, and post-event/rebound windows in UTC.
3. Preserve frozen strategy rules. Evaluate CALL and PUT separately and together; do not retune on event candles.
4. Report trade count, decisive win rate, Wilson interval, net units at 92%, max drawdown, losing streak, signal frequency, and WAIT/no-signal share.
5. Compare strategy results with unconditional next-candle direction and, where feasible, a matched volatility/regime baseline.
6. Report exclusions due to gaps, stale/flat candles, incomplete M5 aggregation, and indicator warm-up.
7. Keep the event study descriptive if the sample is small. One shock episode is not evidence of durable edge.

## Diagnostic implementation
research/stress_test.py provides causal volatility-state diagnostics:
- True range for each candle.
- NORMAL / ELEVATED / EXTREME classification using the median of the preceding 20 true ranges; current candle is excluded from its own baseline.
- Fixed descriptive ratios: ELEVATED at 1.5x and EXTREME at 2.5x prior median true range.
- Trade performance grouped by regime known at signal-candle close.
- Event-window summaries exclude trades settling after the window end.
- Large-body shock-candle detector.

These are descriptive thresholds, not optimized strategy parameters and not an automatic WAIT filter. Future candles cannot alter a past regime assignment.

## Tests
Run from repository root:
```powershell
python -m unittest research.tests.test_stress_test -v
python -m unittest discover -s research/tests -v
```

## Fixed economics and safety
Payout is 92%: win +0.92, loss -1, draw 0. Break-even decisive win rate is 52.0833%. The new code does not open trades, change frozen thresholds, or integrate with the Desktop application.
