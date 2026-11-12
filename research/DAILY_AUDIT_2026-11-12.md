# Daily research audit — 2026-11-12

## Purpose
Run the frozen MEAN_REV_20_Z1.5_CALL only on genuinely new bars after the latest previously inspected snapshot. Do not re-label the already inspected 2026-11-12 00:00–11:55 UTC window as fresh again.

## Frozen boundary
- Previous completed forward snapshot cutoff: 2026-11-12 12:01:06 UTC (run 43213808384).
- Previous fresh period already inspected: 2026-11-12 00:00–11:55 UTC.
- New post-cutoff holdout start: 2026-11-12 12:05:00 UTC. The 12:00 M5 signal candle is not eligible for the new holdout; any settlement crossing this boundary is purged.
- This is a new intraday chronological slice on the same UTC date, not an independent calendar day. Any dependence on the earlier same-day market regime must be disclosed.

## Frozen execution contract
- Prior 20 completed M5 closes; population standard deviation; z-score of the immediately previous close.
- CALL if z <= -1.5, current completed candle bullish, and current close > previous close.
- Signal after candle close; enter next M5 open; settle at close of that entry candle (5 minutes).
- Fixed payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u.
- One active trade per rule, no overlap; gap-separated M5 segments; split-boundary crossings excluded.
- Mirror PUT remains a separate diagnostic. No threshold, direction, expiry, or execution parameter is changed.

## Run status
- Pending fresh Dukascopy download, raw-byte SHA-256, data-integrity audit, frozen backtest, matched same-z baseline, opposite-direction control, and 10,000-replicate random-direction comparison.
- No new performance metrics are asserted in this note. CI success and backtest results will be reported separately.
- Research-only branch; no local user files, production branches, or live trading are involved.
