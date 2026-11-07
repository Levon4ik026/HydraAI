# M5 Bollinger re-entry + Williams %R + ADX — independent rule specification test

> **STATUS UPDATE — 2026-11-07:** Scheduler defects were corrected and the dataset was rerun. The updated corrected results are in the section below. This report uses **92% payout only**; older scenario figures are superseded. The test remains research-only and does not establish a durable edge. See [scheduler audit](M5_SCHEDULER_AUDIT_2026-11-07.md).

Date: 2026-11-07

## Why this test exists
The larger 2026-11-06 screening report found a weak PUT-only M5 lead, but the full historical research CSV used there is not currently accessible through the repository file interface. The repository does contain `eurusd_history_extended.csv`, covering 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC. This note tests a clearly specified, reproducible variant on that shorter sample. It is **not** a reproduction of the earlier screening result because the exact earlier strategy implementation and full source dataset are not available here.

## Data validation
- 30,048 one-minute OHLC rows.
- 0 duplicate timestamps.
- 0 invalid OHLC rows.
- 6,008 complete UTC-aligned M5 candles.
- 2 continuous M5 segments; incomplete buckets and gap-crossing buckets are excluded.
- Chronological split: first 70% train, final 30% holdout; boundary 2026-10-21 19:05 UTC.
- Timestamps interpreted as UTC according to the repository's historical convention.

## Exact tested rule
- Bollinger Bands: 20-period simple moving average, 2 population standard deviations.
- Williams %R: 14 periods.
- ADX: Wilder 14.
- CALL re-entry: previous close below previous lower band, current close back above current lower band; Williams %R crosses upward through -80.
- PUT re-entry: previous close above previous upper band, current close back below current upper band; Williams %R crosses downward through -20.
- ADX regime filter: ADX >= 15, 20, or 25.
- Signal is known after the M5 candle closes. Entry is next M5 candle open; settlement is that candle close.
- Shared CALL/PUT scheduler, no overlapping positions.
- Payout convention: +0.92 per win, -1.00 per loss, 0 for draw. Only the 92% payout assumption is evaluated.

## Results

| ADX minimum | Period | Trades | Wins | Losses | Draws | Win rate (decisive) | Net @92% |
|---:|---|---:|---:|---:|---:|---:|---:|
| 15 | Train | 97 | 48 | 43 | 6 | 52.75% | +1.16 |
| 15 | Holdout | 48 | 31 | 17 | 0 | 64.58% | +11.52 |
| 20 | Train | 77 | 38 | 36 | 3 | 51.35% | -1.04 |
| 20 | Holdout | 39 | 23 | 16 | 0 | 58.97% | +5.16 |
| 25 | Train | 52 | 24 | 26 | 2 | 48.00% | -3.92 |
| 25 | Holdout | 21 | 13 | 8 | 0 | 61.90% | +3.96 |

### Direction breakdown, full sample

| ADX minimum | Direction | Trades | Win rate (decisive) | Net @92% |
|---:|---|---:|---:|---:|
| 15 | CALL | 86 | 62.65% | +16.84 |
| 15 | PUT | 59 | 48.21% | -4.16 |
| 20 | CALL | 68 | 61.76% | +12.64 |
| 20 | PUT | 48 | 42.22% | -8.52 |
| 25 | CALL | 43 | 58.14% | +5.00 |
| 25 | PUT | 30 | 42.86% | -4.96 |

## Interpretation and limits
- This explicitly defined variant is CALL-led on this October sample, opposite to the earlier PUT-only lead. That disagreement is a warning against treating either result as a stable edge.
- The best-looking holdout cell is ADX >=15: 31 wins from 48 decisive trades (64.58%). Its approximate 95% Wilson interval is 50.44%–76.57%, which is wide because the holdout has only 48 trades.
- The ADX >=15 train result is only +1.16 units at 92%. The holdout improvement may be sampling noise or a regime change.
- This sample is short, partly overlaps the period covered by prior research, and does not include real platform quote latency, spread, payout variation, or settlement verification.
- This is a candidate for a longer untouched forward test only. It is **not approved for live trading**, and it does not change the manual-only/no-auto-trading design.

## Next validation
Run this exact frozen rule on a substantially longer dataset not used to select thresholds, with observed per-entry payouts, then report monthly results and confidence intervals. Do not tune the ADX threshold against this holdout.


## Reproducibility confirmation (2026-11-07)

The exact rule is now implemented in `research/reproduce_m5_bb_williams_adx.py` using only the Python standard library. It rebuilds UTC-aligned complete M5 candles from the committed M1 CSV, resets indicators at the two M5 continuity segments, applies one shared non-overlapping scheduler, and uses **0.92 net payout only**.

GitHub Actions run [#42368016020](https://github.com/Levon4ik026/HydraAI/actions/runs/42368016020) completed successfully on `hydra/stabilization`. The seven math-core unit tests passed, and the research step independently reproduced all three frozen holdout outcome counts exactly:
- ADX >= 15: 48 trades, 31 wins, 17 losses, 0 draws; **+11.52 units at 92%**.
- ADX >= 20: 39 trades, 23 wins, 16 losses, 0 draws; **+5.16 units at 92%**.
- ADX >= 25: 21 trades, 13 wins, 8 losses, 0 draws; **+3.96 units at 92%**.

This confirms the calculation is repeatable from repository data; it does not establish a durable trading edge. The holdout is only 48 decisive trades at the best-looking threshold, and it is from the same short October sample used during research. Monthly breakdown is emitted by the script for regime inspection.
