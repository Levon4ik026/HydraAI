# HydraAI — three-candidate prospective forward validation

- Captured UTC: 2026-11-14T07:21:36.630683+00:00
- Branch / code commit: hydra/research-validation / 51b379b6ddcba37ede0025531c559943d4ec14a6
- Forward cohort: 2026-11-10 through requested UTC date 2026-11-13
- Actual forward M1 range: 2026-11-10T00:00:00+00:00 — 2026-11-12T23:58:00+00:00
- Forward M1 rows: 4,305; observed UTC dates: 3
- Warm-up-only M1 range: 2026-11-02T00:00:00+00:00 — 2026-11-09T23:58:00+00:00 (8,617 rows)
- Raw downloaded file SHA-256: ceea96526d3e2535ee4fc6caf694ff943e1c3885810e2538fc894af88b10107d
- Forward-only CSV SHA-256: 7f59e38aa3fd023d5d7d52f0a4b267654845fbb79ceccd2e424be386cb5e0040
- Warm-up-only CSV SHA-256: 81dae08ab585846ee3f83f86321077487822e59a6d430fc945c278fd771556df
- Combined feature-input SHA-256: 5237e571f743196d61a3ce5b1acae17247851a59cb6c1a1eaa45c21444176770
- M5 feature matrix SHA-256: 6ae93313907c40f52abb868c9eff79a20f34ee3d8ba0ee2df0c5731c838b6b25
- Frozen candidate config SHA-256: 23b4689f01687d9a290b050b91be9bb0dc77fe8492cade0e6ac3572a82cad184
- Preregistration protocol SHA-256: 0988e827803a8c5e84f5b4cb608e90b3edbbcc718bdd0924beac896fb98663db

## Data integrity and causal construction

- Raw rows: 12,922; valid unique rows in requested interval: 12,922.
- Invalid rows excluded: 0; identical duplicate timestamps removed: 0; out-of-range rows excluded: 0.
- Forward M1 gaps: 13 intervals, 14 missing minutes; largest interval 2 minutes.
- Warm-up M1 gaps: 18 intervals, 2,902 missing minutes.
- Complete M5 bars from warm-up + forward: 2,563; continuity segments: 26; incomplete UTC-aligned M5 buckets excluded: 29.
- Forward M5 bars: 851; forward segments containing at least one forward bar: 12.
- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.
- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.

## Candidate results

| Candidate | Side / expiry | N | W/L/D | WR excl. draws | Net at 92% | Max DD | Longest L streak | Active days | Trades / active day |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| HYD-CAND-001 | PUT / 5m | 0 | 0/0/0 | n/a | +0.00u | 0.00u | 0 | 0 | 0.00 |
| HYD-CAND-008 | PUT / 30m | 1 | 0/1/0 | 0.00% | -1.00u | 1.00u | 1 | 1 | 1.00 |
| HYD-CAND-010 | CALL / 60m | 5 | 2/3/0 | 40.00% | -1.16u | 1.16u | 1 | 2 | 2.50 |

### Profit concentration

| Candidate | Top UTC day | Top UTC week |
|---|---|---|
| HYD-CAND-001 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-008 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-010 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |

### Payout sensitivity (net units)

| Payout | HYD-CAND-001 | HYD-CAND-008 | HYD-CAND-010 |
|---:|---:|---:|---:|
| 50% | +0.00 | -1.00 | -2.00 |
| 60% | +0.00 | -1.00 | -1.80 |
| 70% | +0.00 | -1.00 | -1.60 |
| 80% | +0.00 | -1.00 | -1.40 |
| 85% | +0.00 | -1.00 | -1.30 |
| 90% | +0.00 | -1.00 | -1.20 |
| 92% | +0.00 | -1.00 | -1.16 |
| 95% | +0.00 | -1.00 | -1.10 |
| 100% | +0.00 | -1.00 | -1.00 |

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

- Raw forward trigger events: 7; accepted trades: 5; overlap-suppressed events: 2.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 5 | 2/3/0 | 40.00% | -1.16 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 5 | 2/3/0 | 40.00% | -1.16 |

## Interpretation and limitations

- Minimum sample threshold: 30 new trades per candidate. At least one candidate is below 30 new trades; results are descriptive only.
- No candidate, signal, threshold, direction, expiry, or entry/settlement convention was added or changed.
- Candidates are not pooled into a portfolio; overlap and capital allocation were not preregistered.
- The 92% payout and sensitivity grid are accounting scenarios, not recorded platform payouts.
- Dukascopy EURUSD BID candles are not Pocket Option executable quotes. Spread, quote construction, actual platform payout, latency, and platform settlement rules are not modeled. These results do not establish executable Pocket Option profitability.
- This is prospective observational validation. Do not tune or gate frozen rules using these forward observations.

## Reproducibility

- Workflow run ID: 43570710605
- Workflow URL: https://github.com/Levon4ik026/HydraAI/actions/runs/43570710605
- Machine-readable manifest: manifest.json.
- Trade-level outcomes: trades.csv.
- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.
