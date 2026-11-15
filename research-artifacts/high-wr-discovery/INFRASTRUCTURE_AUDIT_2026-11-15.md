# HydraAI research infrastructure audit — 2026-11-15

## Scope and safety boundary
This audit and the workflow change are confined to `hydra/research-validation`.
No changes were made to `main`, production, `hydra/stabilization`, the frozen forward candidates HYD-CAND-001 / 008 / 010, or trading execution. No live trades, auto-trading, or OTC instruments were used.

## Verified repository state
- The branch `hydra/research-validation` exists.
- The latest published screen is the five-candidate batch HYD-NEW-001 through HYD-NEW-005, captured 2026-11-15 08:31:32 UTC.
- The report and manifest are committed. They record Dukascopy EUR/USD M1 BID history, the historical split, candidate rules, metrics, source-data SHA-256 and candidate configuration SHA-256.
- The five candidates have negative VALIDATION net units at 92% payout. None meets the report's preliminary performance screen.
- The report says the historical TEST period was previously exposed to broad repository research and is not a pristine holdout.
- The report records zero observations in the new prospective cohort as of capture time.
- The report identifies the full trade ledger as `trades.csv (workflow artifact)`; it was not committed at the expected repository path when this audit was performed. Therefore the reported aggregate figures could not yet be independently recalculated from the branch contents alone.
- The current workflow has only `workflow_dispatch` and path-filtered `push` triggers. It has no scheduled trigger and no mechanism that sends a ChatGPT message. It downloads historical Dukascopy data, runs a fixed five-rule screen, publishes report/manifest/worklog, and uploads a 30-day artifact.
- The fixed candidate list in the screen script is HYD-NEW-001..005. Re-running that script repeats this same fixed set; it is not a general new-hypothesis discovery engine and must not be represented as continuously finding new unique candidates.

## Changes made in this audit
1. Updated `.github/workflows/fifth-wave-fix-session-squeeze-discovery.yml` on this branch only.
2. Added `research-artifacts/high-wr-discovery/latest/trades.csv` to the files committed by the workflow, so the next successful run will preserve the machine-readable trade ledger in the research branch alongside the report and manifest.
3. Extended the uploaded Actions artifact retention from 30 to 90 days as a secondary copy.

## Remaining blockers — explicitly not claimed as solved
- The current five-candidate script does not discover new hypotheses. A genuinely new, deduplicated candidate-generation and screening pipeline must be designed and tested before any recurring schedule is enabled; otherwise a schedule would just rerun the same five candidates and create misleading activity.
- GitHub Actions cannot directly send a message into this ChatGPT conversation. A separate supported notification destination/integration would be required. Until then, report publication in GitHub is not equivalent to a chat notification.
- The committed trade ledger will only appear after the next successful workflow run. It has not been regenerated or independently audited in this commit.
- No workflow run was started by this audit, and no test result is claimed for the workflow edit itself.

## Next verification checklist
- Run the workflow manually on this branch.
- Confirm the run completed successfully and inspect the actual run logs.
- Confirm `latest/trades.csv` is committed and independently recompute per-candidate W/L/D, WR, net units, PF, drawdown and losing streak from it.
- Add unit tests for the candidate screen and an immutable candidate registry before implementing a distinct hypothesis-discovery wave.
- Only after the above exists, add a recurring schedule that generates genuinely new candidates, deduplicates them against the registry/worklog, and emits a batch only when exactly five new candidates pass the declared data-quality and formalization checks.
