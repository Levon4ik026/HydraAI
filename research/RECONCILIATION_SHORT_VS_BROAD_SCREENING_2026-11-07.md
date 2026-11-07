# HydraAI — reconciliation of the short M5 candidate and broad indicator screening

> **STATUS UPDATE — 2026-11-07:** The short-sample M5 test was rerun after fixing the expiry-close scheduler, explicit segment guard, and settlement-time split. Corrected aggregate holdout counts reproduced the previous totals; the updated report now includes direction-specific results and confidence intervals. The broader screening summary remains a separate previously documented result, not affected by this code correction. See [scheduler audit](M5_SCHEDULER_AUDIT_2026-11-07.md) and [corrected rule-test report](M5_BB_Williams_ADX_RULE_TEST_2026-11-07.md).
Date: 2026-11-07
Branch: `hydra/stabilization`
Payout convention: **92% only** (win +0.92, loss -1.00, draw 0).

## Why this audit was needed

The short October M5 test of Bollinger re-entry + Williams %R + ADX produced an attractive 64.58% holdout win rate (31 wins / 17 losses, 48 trades) at ADX >= 15. Before treating that as a candidate, it must be compared with the repository's broader historical screening.

## Broader screening already recorded on main

The report `research/indicator_screening_2026-11-06.md` and its companion `research/indicator_screening_summary.csv` on `main` describe 486,488 M1 candles from 2025-07-21 through 2026-11-05, 68 continuous segments, a chronological 70/30 split, and six fixed indicator combinations across M1/M2/M3/M5.

The screening summary records **24 of 24 strategy/timeframe combinations with negative holdout net results at the 92% payout convention**. Examples:
- M1 BB re-entry + Williams %R + ADX: 4,001 holdout trades, 49.10% wins, -212.68 units.
- M2 Ichimoku: 2,321 holdout trades, 51.00% wins, -45.84 units.
- M5 BB re-entry + Williams %R + ADX (combined directions): 770 holdout trades, 50.81% wins, -18.08 units.
- M5 Supertrend + RSI: 974 holdout trades, 48.15% wins, -71.48 units.

At 92% payout, break-even on decisive outcomes is 52.0833%. The broader screening's best aggregate holdout row is still below break-even and negative in net units.

Source report on main: https://github.com/Levon4ik026/HydraAI/blob/main/research/indicator_screening_2026-11-06.md
Source summary on main: https://github.com/Levon4ik026/HydraAI/blob/main/research/indicator_screening_summary.csv

## Reconciliation with the short October test

The reproducible short-sample test in this branch uses 30,048 M1 candles from 2026-10-07 through 2026-10-28 (6,008 complete UTC-aligned M5 bars, two continuous M5 segments). Its 70/30 holdout contains only 48 trades for ADX >= 15 and yields +11.52 units.

This does **not** overturn the broader screening:
1. The 48-trade holdout is a small slice of one October period.
2. The broader test has thousands of holdout trades and a longer date range.
3. The broad report's M5 combined-direction result is negative; the short test's result is CALL-led, while PUT is negative.
4. The short test and broad screening use different rule implementation/data pipelines; until the long dataset and exact rule code are made reproducible together, their discrepancy is unresolved.

The short test is evidence of a regime-specific historical result, not evidence of a stable edge.

## Decision

- Do not promote this strategy into HydraAI production signals.
- Do not tune ADX thresholds against this same October holdout.
- Keep all results priced at 92%; do not use alternative payout scenarios.
- The next meaningful validation is a frozen, prospective DEMO paper log on the live guest feed, with exact signal timestamp, quoted entry price, payout observed at entry, expiry quote, direction, and outcome. No auto-trading.
- Require a materially larger untouched sample and positive net units across multiple market regimes before considering any production integration.

## Reproducibility status

The short October test is reproducible from the committed branch dataset by `research/reproduce_m5_bb_williams_adx.py`; GitHub Actions run #42368095486 passed both the seven math-core tests and frozen holdout count checks. The 486,488-candle broad screening remains a previously documented result on `main`; its raw `eurusd_research_clean.csv` is not present in the current branch tree, so this audit treats its summary as a referenced prior result rather than claiming to have rerun it here.
