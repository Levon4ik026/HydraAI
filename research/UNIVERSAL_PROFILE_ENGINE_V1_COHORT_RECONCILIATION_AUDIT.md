# Universal candidate profile engine v1 — cohort reconciliation audit

Date: 2026-11-12  
Branch: `hydra/research-validation`  
Profile workflow: [43210692828](https://github.com/Levon4ik026/HydraAI/actions/runs/43210692828)  
Source dataset SHA-256: `4a084d3af598342e2b55e52bb79558825797c64410b875ff8e83ec019972decd`  
M1 rows: 1,061,819; complete M5 bars: 209,936; gap-separated segments: 2,653.  
Feature matrix SHA-256: `7b5640aab878e740e05c5f9b9c856e6b696f45d040c856984bb6800b2c5b1576`.

## Executive result

The universal engine processed 10 frozen candidate definitions. Six reproduced all frozen TRAIN, VALIDATION, and TEST cohort counts exactly. Four reproduced TRAIN and VALIDATION exactly but differed from the historical TEST cohort:

| Candidate | Split | Historical expected W/L/D | Current W/L/D | Difference |
|---|---|---:|---:|---:|
| HYD-CAND-001 | TEST | 124/93/1 (n=218) | 124/94/1 (n=219) | +1 loss, +1 trade |
| HYD-CAND-011 | TEST | 306/282/6 (n=594) | 307/285/6 (n=598) | +1 win, +3 losses, +4 trades |
| HYD-CAND-012 | TEST | 102/86/5 (n=193) | 103/86/5 (n=194) | +1 win, +1 trade |
| HYD-CAND-013 | TEST | 227/206/8 (n=441) | 228/207/8 (n=443) | +1 win, +1 loss, +2 trades |

For all four mismatches, TRAIN and VALIDATION match their frozen cohort counts exactly. This strongly localizes the discrepancies to the recent TEST-period history, rather than indicating a broad split, event, or outcome accounting error. It does **not** prove the provider revised particular bars: the original raw historical CSV was not preserved, so a byte-for-byte old/new data comparison is impossible.

## Candidates passing exact cohort reproduction

HYD-CAND-008, HYD-CAND-003, HYD-CAND-006, HYD-CAND-007, HYD-CAND-010, and HYD-CAND-009 passed all three split gates. This is a reproducibility check only, not a strategy confirmation.

## Legacy rule parity review of the four TEST-only mismatches

A source-level comparison was made against the original candidate definitions:

- **HYD-CAND-001:** the RSI(14) Wilder seed/smoothing and bearish-close level condition match the original expanded-screen convention and the original situation-profile implementation.
- **HYD-CAND-011:** the original eighth-wave event uses the median of the 20 true ranges before the shock candle, then tests the immediately following reversal candle. The universal implementation uses the same prior 20 bars, shock bar, direction and close-through-shock condition.
- **HYD-CAND-012:** the original ninth-wave event uses a fresh EMA20/EMA50 bearish cross and close below EMA20. EMA seeding in the shared matrix matches the original simple-average seed followed by the standard recursive EMA.
- **HYD-CAND-013:** the original eleventh-wave event uses the prior 20 completed true ranges (signal candle excluded), range at least 2.0 times their mean, body/range at least 0.60, bullish close in the upper 25%. The universal rule implements the same conditions.

This source review is supportive, not a substitute for an automated timestamp-by-timestamp parity test on a preserved common raw dataset.

## Required interpretation and safeguards

1. The four failed cohorts are **blocked**. Do not interpret their subgroup profile tables or promote filters from them.
2. Do not silently replace the historic candidate baselines with the current counts. The old registry values remain historical facts tied to a prior, unavailable data snapshot.
3. Do not claim that the new current counts are the old candidate's confirmed replication. They are a new source snapshot run under the same declared rules.
4. The six passing cohorts may be used for descriptive research, but all their profiles remain exploratory. Background rows are overlapping all-eligible-bar benchmarks, not matched non-overlap controls.
5. TEST has prior exploratory exposure and is not pristine independent confirmation.
6. Dukascopy BID bars are a historical proxy, not Pocket Option executable quotes. The 92% payout is a scenario, not guaranteed realized payout.

## Data-integrity correction

The shared data preparation action now pins both the exact expected M1 row count and the expected source SHA-256. It writes the manifest with explicit newline characters and round-trip validates its parsed `rows` and `sha256` fields. This prevents a same-row-count but different-content CSV from being silently accepted by the feature-matrix builder.

## Next validation step

Before interpreting any of the four blocked candidates, run a controlled parity audit that executes the legacy event builders and the universal engine on the exact same current M5 segments, compares raw event timestamps, accepted non-overlap timestamps, and W/L/D outcomes, and reports the first divergence per candidate. Keep the historical baseline separate. Only after this parity audit should the current snapshot be registered as a new cohort version.
