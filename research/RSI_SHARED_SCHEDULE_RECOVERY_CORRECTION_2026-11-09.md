# RSI inversion — shared-schedule recovery and Candidate A correction (2026-11-09)

## Executive correction

The previous follow-up incorrectly withdrew Candidate A. That withdrawal used the wrong candle feature, `(high-close)/pip`, and independently scheduled the filtered CALL subset. The original report's "upper wick" means the **geometric upper wick**:

`(high - max(open, close)) / 0.0001`

It also uses one shared non-overlapping signal schedule across BOTH RSI crossing directions before applying the candidate feature filter. Reconstructing those two details reproduces the original Candidate A trade counts and every W/L/D figure exactly.

This is a substantive correction: Candidate A is restored as a reproducible historical research result. It is still not validated for deployment.

## Frozen signal and schedule

- RSI(14), Wilder smoothing, arithmetic-mean seed over the first 14 close-to-close changes in each uninterrupted segment.
- Completed M1 candle crossing above 70: original CALL; inverse PUT.
- Completed M1 candle crossing below 30: original PUT; inverse CALL.
- One shared lockout across both crossing directions: after an accepted RSI signal, no later raw RSI crossing is eligible until the prior expiry candle has closed.
- Entry at next M1 open; expiry at close of signal index + 15.
- Only after this shared schedule is formed is Candidate A selected: cross-down-30 (therefore inverse CALL) AND geometric upper wick <= 0.1 pip.
- Inverse outcome is exact complement of the original outcome on identical entry and expiry prices. Draws remain draws.
- TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06.
- Fixed hypothetical payout 92%; net = 0.92 × wins − losses.

Dataset is the same 486,488-row EUR/USD M1 BID CSV, 68 continuous segments, SHA-256 `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.

## Exact Candidate A reproduction

| Split | Trades | W | L | D | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,278 | 712 | 548 | 18 | 56.51% | +107.04u |
| VALIDATION | 340 | 178 | 156 | 6 | 53.29% | +7.76u |
| TEST | 312 | 181 | 120 | 11 | 60.13% | +46.52u |
| TOTAL | 1,930 | 1,071 | 824 | 35 | 56.52% | +161.32u |

These match the original pre-entry candle report exactly, including the previously questioned counts. The earlier independent result of only 23 qualifying raw events was not measuring the same feature: it used high-to-close distance, which is not the geometric upper wick. The independent filtered-only schedule also allowed more candidate events than the shared schedule used by the original study.

## TEST monthly breakdown

| Month UTC | Trades | W | L | D | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| 2026-08 | 85 | 49 | 30 | 2 | 62.03% | +15.08u |
| 2026-09 | 105 | 58 | 44 | 3 | 56.86% | +9.36u |
| 2026-10 | 124 | 72 | 51 | 1 | 58.54% | +15.24u |
| 2026-11 partial | 25 | 12 | 13 | 0 | 48.00% | -1.96u |

Correction: these monthly figures follow the recovered shared schedule. They differ from the earlier report's monthly table, which listed 85/111/106/10 trades; that earlier decomposition was based on a different schedule and should be superseded by this report.

## Why this does not yet prove an edge

1. The feature/threshold was discovered after a broad screen; selection and multiple-comparison bias remain.
2. The dataset is Dukascopy BID, not Pocket Option's executable quote/settlement stream.
3. Actual payout per trade, quote-side mismatch, latency, and platform settlement rules are absent.
4. The TEST is already explored, not a pristine holdout. November is only a partial month and currently negative.
5. The strategy's exact scheduling rule is unusual but now explicit: both RSI crossing directions share one position lock, then the geometric wick filter selects the CALL subset. A different scheduling policy produces different trade counts and is not an exact reproduction.

## Reproducibility

New canonical script: `research/rsi_shared_schedule_reproduction.py`

Run:
`python research/rsi_shared_schedule_reproduction.py --data eurusd_research_clean.csv`

It verifies the dataset SHA-256, computes Wilder RSI by uninterrupted segment, builds the shared cross-direction schedule, writes a row-level ledger with signal/entry/expiry timestamps and both original/inverse outcomes, and reports the candidate subset.

## Decision

- Candidate A is **restored as exactly reproduced historical evidence**, not approved as a strategy.
- The earlier claim that Candidate A was impossible is withdrawn.
- Do not tune the wick threshold or add more filters against this already inspected TEST.
- Next valid step is a frozen prospective replay on fresh non-OTC Pocket Option observations with actual entry/settlement quotes, displayed payout, timestamps, all eligible signals and missed signals logged.
- No production HydraAI code or automatic trading has been changed.
