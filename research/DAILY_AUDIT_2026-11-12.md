# Daily research audit — 2026-11-12

## Repository and CI
- Branch HEAD at initial inspection: `hydra/research-validation` = `3b0d440b8665037346f7322a366e8e0188a0a890`; `hydra/stabilization` = `dce8d011ea7f56d7ff890749243ef7d54f0e1afc`; `main` = `b5dc96b089073c72619afafa03428827a92dbbf5`.
- Current research-branch commit set included v3 cross-segment matched-control changes; latest exact-HEAD runs at the time of inspection: feature matrix 43232076249, research validation 43232086183, Math Core 43232086316 — all succeeded.
- At the initial pre-audit HEAD `3b0d440b`, research-validation was 517 commits ahead of stabilization and 608 ahead / 6 behind main. After four audit-only commits, current HEAD is `04723169d3603cad87609f84e3531cd3783f5256`; comparison is now 521 ahead / 0 behind stabilization and 612 ahead / 6 behind main.

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
- Exact-HEAD status for `hydra/stabilization` has no associated Actions run; `main` exact HEAD has a successful run [42798893511](https://github.com/Levon4ik026/HydraAI/actions/runs/42798893511).
- On current exact HEAD `04723169d3603cad87609f84e3531cd3783f5256`, Math Core run [43248028626](https://github.com/Levon4ik026/HydraAI/actions/runs/43248028626) succeeded. Research Validation push [43248013703](https://github.com/Levon4ik026/HydraAI/actions/runs/43248013703) and PR [43248028919](https://github.com/Levon4ik026/HydraAI/actions/runs/43248028919) had their research-unit-tests jobs succeed, while their long-history-reversal jobs were still downloading Dukascopy data; overall runs were not yet complete. The latest shared feature-matrix success [43232076249](https://github.com/Levon4ik026/HydraAI/actions/runs/43232076249) is on ancestor HEAD `3b0d440b`, not the current audit-only HEAD. Its pinned source ends 2026-11-08 23:58 UTC and is not fresh holdout data.
- Exact current HEAD has no failed CI job observed so far; Research Validation remains pending until the long-history jobs finish. Historical failed shared-feature-matrix runs 43215795809 and 43215763592 are explained below in this audit and are fixed in later commits.
- No changes to `main` or `hydra/stabilization`; no PR merge, production promotion, local user-file edit, or trade execution.
