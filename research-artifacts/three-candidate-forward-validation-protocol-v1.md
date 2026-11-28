# Three-candidate prospective validation protocol v1

Status: preregistration only. No forward-period performance result is claimed by this document.

## Scope and freeze
Only the following existing candidates are eligible. Do not add candidates, alter signal definitions, tune thresholds, or select a winner using forward-period results.

- HYD-CAND-001: RSI(14) >= 70 and bearish completed-M5 reversal; PUT; 5-minute expiry.
- HYD-CAND-008: sweep and reclaim of the previous completed UTC week's low; inverse PUT; 30-minute expiry.
- HYD-CAND-010: close breakout below the previous observed completed UTC day's low; exact inverse CALL; 60-minute expiry.

The strategy definitions, signal direction, expiry, and entry convention remain exactly as frozen in `.github/hydra-research/three-candidates-v2.json`. Entry is the next eligible M5 open. Use only completed bars and prior-period levels. Never bridge data gaps or continuity-segment boundaries.

## Forward cohort
The historical snapshot used in the preceding audit ends 2026-11-09 UTC and is already examined. It is not an independent holdout. The forward cohort starts 2026-11-10 00:00 UTC and must end at the latest fully completed UTC date available at capture time. Record exact first/last timestamps, row counts, invalid/duplicate rows, continuity segments, and SHA-256 for the newly captured source file. Keep the historical and forward manifests separate.

Do not publish an inferential conclusion until at least 30 eligible trades per candidate have accumulated; below that threshold report only raw counts and descriptive outcomes. If the feed does not provide sufficient observations, continue collecting rather than backfilling with the previously examined sample.

## Outcome and execution caveats
Report W/L/D, win rate excluding draws, and net units under explicitly stated payout scenarios including 92% and a payout-stress grid. Use +payout for wins, -1 for losses, and 0 for draws. Dukascopy BID candles are a research proxy, not Pocket Option executable quotes; do not claim executable expectancy. Record that spread, quote construction, platform payout, latency, and settlement rules are not modeled unless independently captured.

## Required reporting
For each candidate, report:
- trade count and W/L/D; active UTC days and trades per active day;
- cumulative net units, maximum peak-to-trough drawdown, longest losing streak;
- daily and weekly P&L concentration (top day/week share of total positive P&L, with denominator and caveat when net P&L is near zero or negative);
- payout sensitivity including 92%;
- monthly/weekly stability and calendar-time coverage;
- data gaps, excluded boundary trades, and sample-size limitations.

Do not pool candidates into one portfolio result unless overlap, capital allocation, and simultaneous-signal rules are predeclared.

## Interpretation
This is a prospective observational validation, not a randomized experiment. Do not optimize or gate on forward-period market regimes. Any exploratory regime breakdown must be labelled descriptive and must not change the frozen signal. A positive short sample is not proof of edge; a negative or inconclusive short sample is not grounds for retuning. Preserve this protocol and report deviations explicitly.
