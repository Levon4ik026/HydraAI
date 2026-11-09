# Methodology reconciliation: weak-rule inversion reports (2026-11-09)

## Why this audit exists

The follow-up report `MATCHED_WEAK_RULE_INVERSION_FOLLOWUP_2026-11-09.md` presents a cleaner matched-cohort design than the earlier first screen. However, the two reports are not direct reproductions of one another. Their RSI definitions, signal scheduling, split construction, and candidate rules differ. Their counts and win rates must not be combined or described as one replicated result.

## What the code actually does

### Earlier screen: `inverse_indicator_experiment.py`

- RSI is calculated with pandas `ewm(alpha=1/14, adjust=False, min_periods=14)`; this is not the explicit SMA-seeded Wilder implementation used in the later scripts.
- RSI signals are threshold occupancy: CALL whenever RSI >= 70 and PUT whenever RSI <= 30. They are not threshold-crossing events.
- There is no one-position-per-rule lockout; every eligible candle can create a signal.
- The split is a 70% row-count cut, not the dated TRAIN / VALIDATION / TEST boundaries.
- The script evaluates 1-, 3-, and 5-minute horizons for its primary table. The first-screen report also contains 15-minute figures from other experiment logic, so it should not be treated as the output of this exact script alone.

### Follow-up screen: `matched_weak_rule_inversion_followup.py`

- RSI is explicitly seeded with the first 14 close-to-close changes and then Wilder-smoothed.
- RSI events are threshold crossings: previous RSI <= 70 and current RSI > 70, or previous RSI >= 30 and current RSI < 30.
- A separate non-overlapping lockout is applied per rule; after a signal at index i, the next accepted signal is at i+15 or later.
- Entry is the next candle open; expiry is the close at signal index +15.
- Splits are chronological and date-based: TRAIN before 2026-05-08; VALIDATION through 2026-08-05; TEST from 2026-08-06.
- Direct and inverse outcomes are exact complements on the same accepted cohort. This is the appropriate design for a matched inversion comparison.

## Material discrepancy to preserve

The earlier first-screen report records RSI 15-minute TEST as 1,508 trades, 800 wins, 674 losses, 34 draws (54.27% decisive WR; +62.00 units). The later follow-up report records 1,510 trades, 803 wins, 673 losses, 34 draws (54.40%; +65.76 units).

These figures are not interchangeable. The code confirms that the earlier screen's RSI signal definition is materially different from the later crossing-based, locked schedule. The difference should not be explained away as rounding or treated as a successful exact reproduction.

## Current evidence status

- The later follow-up is the better-defined matched-cohort experiment among the two.
- Its reported RSI result is promising historical evidence, but this audit did not independently rerun the CSV because the dataset identified by SHA-256 `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c` was not present in the current execution workspace.
- Therefore this note is a static methodology/code reconciliation, not a fresh numerical reproduction.
- The follow-up report's five-rule results remain exploratory and subject to selection bias, serial dependence, monthly regime instability, and BID-vs-platform quote mismatch.
- No production code or trading behavior was changed.

## Required next validation

1. Restore the exact CSV and verify its SHA-256 before any rerun.
2. Run the follow-up script unchanged and archive stdout plus the generated row-level ledger.
3. Add an explicit invariant check: for every accepted event, direct W equals inverse L, direct L equals inverse W, and draws remain draws; entry and expiry timestamps/prices must be identical.
4. For any new candidate, freeze the rule and horizon before evaluating a fresh chronological holdout. Do not select the best horizon or rule on the already inspected TEST.
5. The next meaningful external validation is prospective, non-OTC Pocket Option DEMO capture with actual platform quotes, displayed payout, signal timestamp, decision timestamp, and measured execution delay. Keep manual-only; no auto-trading.
