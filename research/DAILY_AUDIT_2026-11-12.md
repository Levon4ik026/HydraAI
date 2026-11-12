# Daily research audit — 2026-11-12

## Repository and CI
- Branch HEAD at initial inspection: `hydra/research-validation` = `3b0d440b8665037346f7322a366e8e0188a0a890`; `hydra/stabilization` = `dce8d011ea7f56d7ff890749243ef7d54f0e1afc`; `main` = `b5dc96b089073c72619afafa03428827a92dbbf5`.
- Current research-branch commit set included v3 cross-segment matched-control changes; latest exact-HEAD runs at the time of inspection: feature matrix 43232076249, research validation 43232086183, Math Core 43232086316 — all succeeded.
- Branch comparison: research-validation is 517 commits ahead of stabilization, 0 behind; versus main it is 608 ahead and 6 behind.
- No CI failure on the exact inspected HEAD.

## Frozen MEAN_REV forward boundary
- Previous completed forward snapshot cutoff: 2026-11-12 12:01:06 UTC (run 43213808384).
- Previously inspected fresh period: 2026-11-12 00:00–11:55 UTC.
- The only genuinely new same-day interval after that snapshot would begin with a signal candle at 12:05 UTC. The 12:00 M5 signal candle and any trade whose settlement crosses the 12:05 boundary must be excluded.
- The checked-in workflow currently hardcodes the holdout start to current UTC midnight and has no supported input for a post-cutoff intraday boundary. Re-running it now would reclassify the already inspected 00:00–11:55 interval as fresh. That would violate the user's untouched-holdout requirement.
- Therefore **no independent post-cutoff backtest was run in this automation pass**. No fresh metrics are claimed. The earlier Nov 12 sample remains the only verified holdout for that day; it is not being relabelled.

## Frozen execution contract (unchanged)
- Prior 20 completed M5 closes; population standard deviation; z-score of the immediately previous close.
- CALL if z <= -1.5, current completed candle bullish, and current close > previous close.
- Signal after close; entry next M5 open; settlement at close of entry candle (5 minutes).
- Fixed payout 92%; WIN +0.92u, LOSS -1u, DRAW 0u.
- One active trade per rule, no overlap; gap-separated M5 segments; split-boundary crossings purged.
- Mirror PUT remains a separate diagnostic. No threshold, direction, expiry, or execution parameter changed.

## Data availability and limitation
- The prior run used Dukascopy EURUSD M1 BID and reported snapshot cutoff 12:01:06 UTC, 1,066,844 valid M1 rows, 210,931 complete M5 bars, 2,666 continuity segments, and source SHA-256 `a63ab1b0219617720ce76c6a1a077a2980b5a9b03aca5afa9245c4cbfb2bc570`.
- That source hash and snapshot describe the prior run only. A new raw snapshot was not downloaded in this pass, so no newer source coverage, row count, continuity count, timestamp range, or hash is asserted.
- The mean-reversion workflow itself is available, but the GitHub connector exposed no workflow-dispatch action, and a safe post-cutoff run boundary could not be supplied through the current workflow. The attempted temporary override file was removed; no workflow or strategy code was changed.

## Other research/CI observations
- Latest research HEAD has successful exact-SHA runs for the shared M5 feature matrix, research validation, and Math Core.
- Historical failed shared-feature-matrix runs 43215795809 and 43215763592 are being inspected separately; they do not affect the successful current-HEAD CI status.
- No changes to `main` or `hydra/stabilization`; no PR merge, production promotion, local user-file edit, or trade execution.
