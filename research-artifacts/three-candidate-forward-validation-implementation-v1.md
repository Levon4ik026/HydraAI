# Three-candidate forward pipeline implementation note

Status: pipeline and tests added on hydra/research-validation. The first prospective run must be confirmed from its own GitHub Actions run and report; this note does not claim that a forward backtest has already completed.

## Frozen scope

The pipeline accepts exactly HYD-CAND-001, HYD-CAND-008 and HYD-CAND-010 from .github/hydra-research/three-candidates-v2.json. It fails closed if the event type, direction, expiry bars, overlap policy, warm-up index, tail guard, required prior-period level, or close-settlement convention differs from the frozen definitions.

No other candidate is evaluated. No signal, threshold, expiry, entry rule or settlement convention is optimized.

## Data handling

- Downloaded source: Dukascopy EURUSD M1 BID.
- Warm-up: 2026-11-02 through 2026-11-09 UTC. It initializes RSI/other causal features and the previous observed completed UTC day/week levels only. Warm-up signals and outcomes are never scored.
- Forward cohort: from 2026-11-10 00:00 UTC through the latest completed UTC weekday requested by the workflow.
- The pipeline writes separate warmup-only and forward-only CSV files and SHA-256 values, plus a combined feature input used only to build the causal M5 matrix.
- Invalid rows are excluded and counted. Identical duplicate timestamps are removed and counted; conflicting duplicates fail the run. Out-of-range rows are excluded and counted.
- M5 bars are UTC-aligned and must contain all five M1 rows. The existing M5 builder starts a new continuity segment at every missing M5 bucket. Indicators are computed only inside each segment.
- Prior day/week levels are generated from previously observed completed UTC periods. Forward outcomes are never used to construct a prior level.
- The existing universal_profile_engine evaluates the unchanged candidate events. The forward split boundary is 2026-11-10; any trade whose settlement crosses that boundary is purged. Entry is the next eligible M5 open and settlement is the expiry bar close in the same segment.

## Outputs

The workflow artifact retains the raw download, warm-up-only CSV, forward-only CSV, combined feature input, causal M5 feature matrix, trade ledger, JSON manifest and Markdown report. The report, manifest and trade ledger are also published on the research branch under research-artifacts/forward-validation/.

The manifest records source/config/protocol/script/matrix SHA-256 values, timestamp ranges, row counts, invalid/duplicate/out-of-range rows, data gaps, incomplete M5 buckets, continuity segments and per-candidate metrics.

## Daily execution on the research branch

The workflow is push-triggered only on hydra/research-validation. A GitHub scheduled workflow would execute only from the repository default branch, so this implementation does not add a schedule to main. The existing daily automation triggers a new branch-only run by updating forward-validation-run-trigger.txt, then checks the workflow and report. Workflow report commits do not match the trigger paths, preventing a report-commit loop.

## Limits

A candidate needs at least 30 new forward trades before any inferential discussion; below that, only descriptive counts/outcomes are reported. The 92% payout and sensitivity grid are scenarios, not measured platform payouts. Dukascopy BID is not Pocket Option executable pricing; spread, quote construction, payout variation, latency and platform settlement are not modeled. No executable profitability is claimed.
