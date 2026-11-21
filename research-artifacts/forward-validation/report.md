# HydraAI — three-candidate prospective forward validation

- Captured UTC: 2026-11-21T07:22:26.856123+00:00
- Branch / code commit: hydra/research-validation / cf1b390086678a311f9f85784e6aa9feba3b56d6
- Forward cohort: 2026-11-10 through requested UTC date 2026-11-20
- Actual forward M1 range: 2026-11-10T00:00:00+00:00 — 2026-11-20T21:59:00+00:00
- Forward M1 rows: 12,819; observed UTC dates: 10
- Warm-up-only M1 range: 2026-11-02T00:00:00+00:00 — 2026-11-09T23:59:00+00:00 (8,619 rows)
- Raw downloaded file SHA-256: cf10874b0405a3e21fab144d9c1799ad131a10a0e2fc19a6a89affbe353c3f92
- Forward-only CSV SHA-256: 3b0adcae7780b68113645a1ffe5c12ef3119ae8b9bc96d1b0cec30e0ce78f660
- Warm-up-only CSV SHA-256: 7d9548d701297dea295c262ece21f0e6c63201fe89e31e7b813d2d65fc87fca8
- Combined feature-input SHA-256: c11d571c9c877bcb0977ba640237826587b81e05a041f24eb7338b8d971f9e23
- M5 feature matrix SHA-256: 7ec5c82659b129b196ae1502d7f0395c120246c2a35a1a59040c1d61b3f4fb31
- Frozen candidate config SHA-256: 23b4689f01687d9a290b050b91be9bb0dc77fe8492cade0e6ac3572a82cad184
- Preregistration protocol SHA-256: 0988e827803a8c5e84f5b4cb608e90b3edbbcc718bdd0924beac896fb98663db

## Data integrity and causal construction

- Raw rows: 21,438; valid unique rows in requested interval: 21,438.
- Invalid rows excluded: 0; identical duplicate timestamps removed: 0; out-of-range rows excluded: 0.
- Forward M1 gaps: 19 intervals, 2,901 missing minutes; largest interval 2,881 minutes.
- Warm-up M1 gaps: 17 intervals, 2,901 missing minutes.
- Complete M5 bars from warm-up + forward: 4,264; continuity segments: 29; incomplete UTC-aligned M5 buckets excluded: 32.
- Forward M5 bars: 2,550; forward segments containing at least one forward bar: 17.
- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.
- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.

## Candidate results

| Candidate | Side / expiry | N | W/L/D | Decisive WR [95% Wilson] | Wins / all | Net @92% | ROI | PF | Max DD | Longest L streak | Raw signals | Trade freq / M5 | WAIT |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HYD-CAND-001 | PUT / 5m | 15 | 7/8/0 | 46.67% [24.81, 69.88]% | 46.67% | -1.56u | -10.40% | 0.81 | 3.08u | 2 | 15 | 0.588% | 99.412% |
| HYD-CAND-008 | PUT / 30m | 6 | 4/2/0 | 66.67% [30.00, 90.32]% | 66.67% | +1.68u | 28.00% | 1.84 | 2.00u | 2 | 8 | 0.235% | 99.765% |
| HYD-CAND-010 | CALL / 60m | 21 | 9/12/0 | 42.86% [24.47, 63.45]% | 42.86% | -3.72u | -17.71% | 0.69 | 5.32u | 5 | 34 | 0.824% | 99.176% |

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
| 50% | -4.50 | +0.00 | -7.50 |
| 60% | -3.80 | +0.40 | -6.60 |
| 70% | -3.10 | +0.80 | -5.70 |
| 80% | -2.40 | +1.20 | -4.80 |
| 85% | -2.05 | +1.40 | -4.35 |
| 90% | -1.70 | +1.60 | -3.90 |
| 92% | -1.56 | +1.68 | -3.72 |
| 95% | -1.35 | +1.80 | -3.45 |
| 100% | -1.00 | +2.00 | -3.00 |

### HYD-CAND-001 — weekly/monthly stability

- Raw forward trigger events: 15; accepted trades: 15; overlap-suppressed events: 0.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 0 | 0/0/0 | n/a | +0.00 |
| 2026-W47 | 15 | 7/8/0 | 46.67% | -1.56 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 15 | 7/8/0 | 46.67% | -1.56 |

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

- Workflow run ID: 44879924801
- Workflow URL: https://github.com/Levon4ik026/HydraAI/actions/runs/44879924801
- Machine-readable manifest: manifest.json.
- Trade-level outcomes: trades.csv.
- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.
