# Paired inversion audit — 2026-11-09

## Purpose
Resolve the arithmetic question: if a directional strategy wins 33% of the time, must its exact inverse win 67%?

**Yes, on the identical set of decisive trades.** For each fixed signal, entry and expiry, CALL↔PUT reversal swaps every win and loss. Therefore:
- direct wins + inverse wins = decisive trades;
- direct hit rate + inverse hit rate = 100%, when draws are excluded from both denominators;
- draws remain draws after inversion and must be handled separately.

If this identity fails, the two calculations did not use the same trades/outcomes, or there is a coding/denominator bug.

## Re-run performed
Dataset: `eurusd_research_clean.csv`
- 486,488 EUR/USD M1 candles
- 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC
- Chronological split: first 70% TRAIN, final 30% TEST; boundary 2026-06-17 04:44 UTC.
- Signal at candle close; entry at next candle open; expiry at close after 1, 3 or 5 one-minute rows.
- Indicator calculations reset at timestamp gaps; expiry cannot cross a gap.
- Ties are draws and excluded symmetrically.
- The paired audit was rerun from the CSV. All 30 rule/expiry/split combinations passed the exact integer complement check.

## Exact holdout results
| Rule | Expiry | Signals | Decisive | Draws | Direct wins | Inverse wins | Direct rate | Inverse rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EMA9/21 trend | 1m | 145,526 | 133,943 | 11,583 | 66,076 | 67,867 | 49.340% | 50.660% |
| EMA9/21 trend | 3m | 145,484 | 139,132 | 6,352 | 68,382 | 70,750 | 49.147% | 50.853% |
| EMA9/21 trend | 5m | 145,442 | 140,644 | 4,798 | 69,032 | 71,612 | 49.077% | 50.923% |
| MOM5 trend | 1m | 141,012 | 130,037 | 10,975 | 63,429 | 66,608 | 48.782% | 51.218% |
| MOM5 trend | 3m | 140,972 | 134,970 | 6,002 | 65,806 | 69,164 | 48.728% | 51.272% |
| MOM5 trend | 5m | 140,932 | 136,393 | 4,539 | 66,823 | 69,570 | 48.986% | 51.014% |
| RSI extreme momentum | 1m | 12,119 | 11,239 | 880 | 5,428 | 5,811 | 48.296% | 51.704% |
| RSI extreme momentum | 3m | 12,113 | 11,616 | 497 | 5,551 | 6,065 | 47.788% | 52.212% |
| RSI extreme momentum | 5m | 12,107 | 11,763 | 344 | 5,585 | 6,178 | 47.479% | 52.521% |
| RSI extreme fade | 1m | 12,119 | 11,239 | 880 | 5,811 | 5,428 | 51.704% | 48.296% |
| RSI extreme fade | 3m | 12,113 | 11,616 | 497 | 6,065 | 5,551 | 52.212% | 47.788% |
| RSI extreme fade | 5m | 12,107 | 11,763 | 344 | 6,178 | 5,585 | 52.521% | 47.479% |
| Bollinger 20/2 fade | 1m | 16,860 | 15,680 | 1,180 | 8,285 | 7,395 | 52.838% | 47.162% |
| Bollinger 20/2 fade | 3m | 16,853 | 16,183 | 670 | 8,567 | 7,616 | 52.946% | 47.054% |
| Bollinger 20/2 fade | 5m | 16,843 | 16,315 | 528 | 8,609 | 7,706 | 52.790% | 47.210% |

## The important example
The RSI-extreme momentum rule at 5-minute expiry had 5,585 direct wins and 6,178 losses among 11,763 decisive holdout outcomes:
- direct: 5,585 / 11,763 = **47.479%**
- exact inverse: 6,178 / 11,763 = **52.521%**
- sum: **100.000%**

This is not a 33% strategy. None of the five simple rules in this experiment produced a 33% holdout hit rate. Therefore this run does not establish what happened to the separate ~33% result discussed earlier. We must identify that exact earlier strategy/test and invert its original trade list; we should not substitute the RSI example.

## Payout reality
At a fixed 92% net payout, break-even is 52.083%. The inverse RSI momentum rule's holdout EV estimates are:
- 1m: 51.704%, negative EV;
- 3m: 52.212%, approximately +0.0025 units per unit stake;
- 5m: 52.521%, approximately +0.0084 units per unit stake.

These tiny positive estimates are not evidence of a robust tradable edge. Signals overlap heavily, trades are not independent, payout may vary, and no execution friction is modelled. No strategy is approved for HydraAI signals based on this experiment.

## Correction to the earlier report
The earlier report included a non-overlapping/cooldown table (5,317 and 3,969 trades) that was not independently reproduced in this audit. Treat those figures and associated confidence intervals/p-values as **unverified**; they are intentionally not repeated as validated results here. The exact rerun above also gives slightly different final decimal rounding from the earlier report. The paired integer counts are the authoritative audit output.

## Next required step
Find the original test that produced the ~33% win rate, recover its exact signal/trade rows, and calculate the inverse on those same rows. If the original has 33% wins and 67% losses (no draws), its inverse must be 67%. If it does not, the discrepancy will be traceable to changed sample, timing, ties, or a bug.
