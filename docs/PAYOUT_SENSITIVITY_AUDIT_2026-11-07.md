# Historical payout sensitivity and audit — 2026-11-07

## Scope
This note reprices the existing `backtest_v3` HOLDOUT trade logs without changing their WIN/LOSS/DRAW outcomes. It does not rerun indicators or repair the underlying signal-generation defects. The files cover October 2026 only; they are a narrow diagnostic, not an independent validation set.

## Repricing results
Net units are calculated as wins × assumed net payout − losses. Draws contribute zero.

| Horizon | Direction | Trades | Win rate excluding draws | Break-even net payout | Net @80% | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| M1 | CALL | 1,380 | 56.24% | 0.778 | +13.80 | +88.92 |
| M1 | PUT | 1,991 | 30.52% | 2.277 | -827.00 | -759.80 |
| M3 | CALL | 776 | 52.27% | 0.913 | -40.40 | +2.44 |
| M3 | PUT | 1,113 | 35.95% | 1.782 | -360.40 | -316.36 |
| M5 | CALL | 564 | 54.83% | 0.824 | -6.80 | +27.28 |
| M5 | PUT | 791 | 41.78% | 1.393 | -181.00 | -144.40 |
| M10 | CALL | 352 | 42.77% | 1.338 | -71.60 | -55.64 |
| M10 | PUT | 478 | 36.96% | 1.706 | -154.00 | -133.60 |

## Interpretation
- The old EMA20/EMA50 + RSI14 rules are strongly direction-asymmetric in these logs: PUT is poor at all tested horizons.
- M1 CALL looks promising in this single month, but cannot be accepted as an edge: the old `backtest_v3.py` calculates EMA/RSI across data gaps, and CALL/PUT were backtested independently. The logs therefore do not establish a globally non-overlapping CALL+PUT portfolio.
- M3 CALL only becomes slightly positive under a 92% payout assumption; the margin is negligible and highly sensitive to actual payout.
- M5 CALL is slightly negative at 80% and positive at 92%, demonstrating why payout must be recorded per trade rather than hard-coded.
- These logs are not evidence of stable performance across seasons or regimes. No live/demo recommendation follows.

## Required next validation
1. Rebuild signals from raw OHLC with the gap-aware engine.
2. Use a single shared CALL/PUT scheduler.
3. Reprice using observed payout for each entry; report 80/85/90/92/95% scenarios only as sensitivity analysis.
4. Preserve a chronological untouched test period and report monthly/regime breakdowns.
5. Verify actual Pocket Option quote timing and expiry settlement before comparing simulated results to platform outcomes.

## Reproducibility note
The source historical CSV exists in the repository tree but the current GitHub file-fetch interface returned an empty body for that file, so this note deliberately uses only the small, retrievable trade-log CSVs. It does not claim a fresh full-history rerun.
