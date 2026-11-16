# HydraAI — three-candidate prospective forward validation

- Captured UTC: 2026-11-16T08:08:17.929497+00:00
- Branch / code commit: hydra/research-validation / 115e32772c04a1e5b9f13200abe1bb845a8d0eb2
- Forward cohort: 2026-11-10 through requested UTC date 2026-11-13
- Actual forward M1 range: 2026-11-10T00:00:00+00:00 — 2026-11-13T21:59:00+00:00
- Forward M1 rows: 5,625; observed UTC dates: 4
- Warm-up-only M1 range: 2026-11-02T00:00:00+00:00 — 2026-11-09T23:58:00+00:00 (8,618 rows)
- Raw downloaded file SHA-256: ba81dc250f6bc62358b1bc2949f81dc3eaa5bdc127a16e79d3db9307f26b7c06
- Forward-only CSV SHA-256: c2032d38d4692afbd19fd225341e22c2101a466bd1f9f158482e4542e7804e02
- Warm-up-only CSV SHA-256: f639f781a58e9d94e017f5f8f75568220c49f586c5a9471e66742ab59e41c476
- Combined feature-input SHA-256: c3f606122b6e18bb511e16e54e696b97bbe1f8a226a01d9aa9d9c7bb601eac75
- M5 feature matrix SHA-256: 9da84f70e9f75918a6d6e7d5eb1de364d9917aa565e617bd2a5eac27cc267576
- Frozen candidate config SHA-256: 23b4689f01687d9a290b050b91be9bb0dc77fe8492cade0e6ac3572a82cad184
- Preregistration protocol SHA-256: 0988e827803a8c5e84f5b4cb608e90b3edbbcc718bdd0924beac896fb98663db

## Data integrity and causal construction

- Raw rows: 14,243; valid unique rows in requested interval: 14,243.
- Invalid rows excluded: 0; identical duplicate timestamps removed: 0; out-of-range rows excluded: 0.
- Forward M1 gaps: 14 intervals, 15 missing minutes; largest interval 2 minutes.
- Warm-up M1 gaps: 17 intervals, 2,901 missing minutes.
- Complete M5 bars from warm-up + forward: 2,828; continuity segments: 26; incomplete UTC-aligned M5 buckets excluded: 28.
- Forward M5 bars: 1,115; forward segments containing at least one forward bar: 13.
- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.
- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.

## Candidate results

| Candidate | Side / expiry | N | W/L/D | Decisive WR [95% Wilson] | Wins / all | Net @92% | ROI | PF | Max DD | Longest L streak | Raw signals | Trade freq / M5 | WAIT |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HYD-CAND-001 | PUT / 5m | 0 | 0/0/0 | n/a n/a | n/a | +0.00u | n/a | n/a | 0.00u | 0 | 0 | 0.000% | 100.000% |
| HYD-CAND-008 | PUT / 30m | 1 | 0/1/0 | 0.00% [0.00, 79.35]% | 0.00% | -1.00u | -100.00% | 0.00 | 1.00u | 1 | 1 | 0.090% | 99.910% |
| HYD-CAND-010 | CALL / 60m | 6 | 3/3/0 | 50.00% [18.76, 81.24]% | 50.00% | -0.24u | -4.00% | 0.92 | 1.16u | 1 | 8 | 0.538% | 99.462% |

- Wilson 95% intervals use decisive outcomes (W+L) and assume independent outcomes; serial clustering makes them descriptive, especially at small N.
- Trade frequency is accepted non-overlapping trades divided by complete forward M5 bars; WAIT is its complement. Raw trigger events are shown separately.

### Profit concentration

| Candidate | Top UTC day | Top UTC week |
|---|---|---|
| HYD-CAND-001 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-008 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-010 | 2026-11-13: 100.00% of +0.92u positive period net | n/a (no positive period net P&L) |

### Payout sensitivity (net units)

| Payout | HYD-CAND-001 | HYD-CAND-008 | HYD-CAND-010 |
|---:|---:|---:|---:|
| 50% | +0.00 | -1.00 | -1.50 |
| 60% | +0.00 | -1.00 | -1.20 |
| 70% | +0.00 | -1.00 | -0.90 |
| 80% | +0.00 | -1.00 | -0.60 |
| 85% | +0.00 | -1.00 | -0.45 |
| 90% | +0.00 | -1.00 | -0.30 |
| 92% | +0.00 | -1.00 | -0.24 |
| 95% | +0.00 | -1.00 | -0.15 |
| 100% | +0.00 | -1.00 | +0.00 |

### HYD-CAND-001 — weekly/monthly stability

- Raw forward trigger events: 0; accepted trades: 0; overlap-suppressed events: 0.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 0 | 0/0/0 | n/a | +0.00 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 0 | 0/0/0 | n/a | +0.00 |

### HYD-CAND-008 — weekly/monthly stability

- Raw forward trigger events: 1; accepted trades: 1; overlap-suppressed events: 0.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 1 | 0/1/0 | 0.00% | -1.00 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 1 | 0/1/0 | 0.00% | -1.00 |

### HYD-CAND-010 — weekly/monthly stability

- Raw forward trigger events: 8; accepted trades: 6; overlap-suppressed events: 2.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 6 | 3/3/0 | 50.00% | -0.24 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 6 | 3/3/0 | 50.00% | -0.24 |

## Interpretation and limitations

- Minimum sample threshold: 30 new trades per candidate. At least one candidate is below 30 new trades; results are descriptive only.
- No candidate, signal, threshold, direction, expiry, or entry/settlement convention was added or changed.
- Candidates are not pooled into a portfolio; overlap and capital allocation were not preregistered.
- The 92% payout and sensitivity grid are accounting scenarios, not recorded platform payouts.
- Dukascopy EURUSD BID candles are not Pocket Option executable quotes. Spread, quote construction, actual platform payout, latency, and platform settlement rules are not modeled. These results do not establish executable Pocket Option profitability.
- This is prospective observational validation. Do not tune or gate frozen rules using these forward observations.

## Reproducibility

- Workflow run ID: 43828801852
- Workflow URL: https://github.com/Levon4ik026/HydraAI/actions/runs/43828801852
- Machine-readable manifest: manifest.json.
- Trade-level outcomes: trades.csv.
- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.
