# HydraAI — three-candidate prospective forward validation

- Captured UTC: 2026-11-19T07:07:59.228566+00:00
- Branch / code commit: hydra/research-validation / 93695cfcb2e1b48da4192e8eb074a616b973ca56
- Forward cohort: 2026-11-10 through requested UTC date 2026-11-18
- Actual forward M1 range: 2026-11-10T00:00:00+00:00 — 2026-11-18T23:58:00+00:00
- Forward M1 rows: 10,061; observed UTC dates: 8
- Warm-up-only M1 range: 2026-11-02T00:00:00+00:00 — 2026-11-09T23:59:00+00:00 (8,619 rows)
- Raw downloaded file SHA-256: 6877c125ab24bb9ae5b69ac09f4d1fd194d71d50689a491c8fb86208c3a5ead4
- Forward-only CSV SHA-256: 6ff8760a3a93e77327fa4b03059e863c34c0a96b679c2bf0a6c458c39fa4636a
- Warm-up-only CSV SHA-256: 7d9548d701297dea295c262ece21f0e6c63201fe89e31e7b813d2d65fc87fca8
- Combined feature-input SHA-256: 14f9f71168602c73d2fa639321932ee46c2ddc2d7ea648cbf2f580062440d58e
- M5 feature matrix SHA-256: 5d485315964654d42e3e0d6572047d10537c9be817edf5ce529bc311940d19d9
- Frozen candidate config SHA-256: 23b4689f01687d9a290b050b91be9bb0dc77fe8492cade0e6ac3572a82cad184
- Preregistration protocol SHA-256: 0988e827803a8c5e84f5b4cb608e90b3edbbcc718bdd0924beac896fb98663db

## Data integrity and causal construction

- Raw rows: 18,680; valid unique rows in requested interval: 18,680.
- Invalid rows excluded: 0; identical duplicate timestamps removed: 0; out-of-range rows excluded: 0.
- Forward M1 gaps: 17 intervals, 2,898 missing minutes; largest interval 2,881 minutes.
- Warm-up M1 gaps: 17 intervals, 2,901 missing minutes.
- Complete M5 bars from warm-up + forward: 3,713; continuity segments: 27; incomplete UTC-aligned M5 buckets excluded: 31.
- Forward M5 bars: 1,999; forward segments containing at least one forward bar: 15.
- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.
- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.

## Candidate results

| Candidate | Side / expiry | N | W/L/D | Decisive WR [95% Wilson] | Wins / all | Net @92% | ROI | PF | Max DD | Longest L streak | Raw signals | Trade freq / M5 | WAIT |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HYD-CAND-001 | PUT / 5m | 1 | 0/1/0 | 0.00% [0.00, 79.35]% | 0.00% | -1.00u | -100.00% | 0.00 | 1.00u | 1 | 1 | 0.050% | 99.950% |
| HYD-CAND-008 | PUT / 30m | 6 | 4/2/0 | 66.67% [30.00, 90.32]% | 66.67% | +1.68u | 28.00% | 1.84 | 2.00u | 2 | 8 | 0.300% | 99.700% |
| HYD-CAND-010 | CALL / 60m | 21 | 9/12/0 | 42.86% [24.47, 63.45]% | 42.86% | -3.72u | -17.71% | 0.69 | 5.32u | 5 | 34 | 1.051% | 98.949% |

- Wilson 95% intervals use decisive outcomes (W+L) and assume independent outcomes; serial clustering makes them descriptive, especially at small N.
- Trade frequency is accepted non-overlapping trades divided by complete forward M5 bars; WAIT is its complement. Raw trigger events are shown separately.

### Profit concentration

| Candidate | Top UTC day | Top UTC week |
|---|---|---|
| HYD-CAND-001 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-008 | 2026-11-16: 65.67% of +2.68u positive period net | 2026-W47: 100.00% of +2.68u positive period net |
| HYD-CAND-010 | 2026-11-17: 65.67% of +2.68u positive period net | n/a (no positive period net P&L) |

### Payout sensitivity (net units)

| Payout | HYD-CAND-001 | HYD-CAND-008 | HYD-CAND-010 |
|---:|---:|---:|---:|
| 50% | -1.00 | +0.00 | -7.50 |
| 60% | -1.00 | +0.40 | -6.60 |
| 70% | -1.00 | +0.80 | -5.70 |
| 80% | -1.00 | +1.20 | -4.80 |
| 85% | -1.00 | +1.40 | -4.35 |
| 90% | -1.00 | +1.60 | -3.90 |
| 92% | -1.00 | +1.68 | -3.72 |
| 95% | -1.00 | +1.80 | -3.45 |
| 100% | -1.00 | +2.00 | -3.00 |

### HYD-CAND-001 — weekly/monthly stability

- Raw forward trigger events: 1; accepted trades: 1; overlap-suppressed events: 0.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 0 | 0/0/0 | n/a | +0.00 |
| 2026-W47 | 1 | 0/1/0 | 0.00% | -1.00 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 1 | 0/1/0 | 0.00% | -1.00 |

### HYD-CAND-008 — weekly/monthly stability

- Raw forward trigger events: 8; accepted trades: 6; overlap-suppressed events: 2.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 1 | 0/1/0 | 0.00% | -1.00 |
| 2026-W47 | 5 | 4/1/0 | 80.00% | +2.68 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 6 | 4/2/0 | 66.67% | +1.68 |

### HYD-CAND-010 — weekly/monthly stability

- Raw forward trigger events: 34; accepted trades: 21; overlap-suppressed events: 13.
- Boundary-crossing M5 windows purged: 9; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 6 | 3/3/0 | 50.00% | -0.24 |
| 2026-W47 | 15 | 6/9/0 | 40.00% | -3.48 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 21 | 9/12/0 | 42.86% | -3.72 |

## Interpretation and limitations

- Minimum sample threshold: 30 new trades per candidate. At least one candidate is below 30 new trades; results are descriptive only.
- No candidate, signal, threshold, direction, expiry, or entry/settlement convention was added or changed.
- Candidates are not pooled into a portfolio; overlap and capital allocation were not preregistered.
- The 92% payout and sensitivity grid are accounting scenarios, not recorded platform payouts.
- Dukascopy EURUSD BID candles are not Pocket Option executable quotes. Spread, quote construction, actual platform payout, latency, and platform settlement rules are not modeled. These results do not establish executable Pocket Option profitability.
- This is prospective observational validation. Do not tune or gate frozen rules using these forward observations.

## Reproducibility

- Workflow run ID: 44477227941
- Workflow URL: https://github.com/Levon4ik026/HydraAI/actions/runs/44477227941
- Machine-readable manifest: manifest.json.
- Trade-level outcomes: trades.csv.
- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.
