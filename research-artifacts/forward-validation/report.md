# HydraAI — three-candidate prospective forward validation

- Captured UTC: 2026-11-17T07:24:44.105170+00:00
- Branch / code commit: hydra/research-validation / e5ee74d48577f576815d04ee090d1b5a8c623e3c
- Forward cohort: 2026-11-10 through requested UTC date 2026-11-16
- Actual forward M1 range: 2026-11-10T00:00:00+00:00 — 2026-11-16T23:58:00+00:00
- Forward M1 rows: 7,181; observed UTC dates: 6
- Warm-up-only M1 range: 2026-11-02T00:00:00+00:00 — 2026-11-09T23:59:00+00:00 (8,619 rows)
- Raw downloaded file SHA-256: 6d53ef50d5bf22e4f05f9ec82b37712dd3ca23867eaae1a11bcc4c994d849c45
- Forward-only CSV SHA-256: 155b2f26f30ed2e62409c2f6525aa55a60137a2206517769f3fd2b8b68bb8fae
- Warm-up-only CSV SHA-256: 7d9548d701297dea295c262ece21f0e6c63201fe89e31e7b813d2d65fc87fca8
- Combined feature-input SHA-256: 31a20a1b5fb83725d61b4fd703a4595ac0d865858e351b3605c771ba077e018d
- M5 feature matrix SHA-256: 8daf0d3ce09438c53092653a60d578a5052adf4c43a3cf454612fe3e5f25b610
- Frozen candidate config SHA-256: 23b4689f01687d9a290b050b91be9bb0dc77fe8492cade0e6ac3572a82cad184
- Preregistration protocol SHA-256: 0988e827803a8c5e84f5b4cb608e90b3edbbcc718bdd0924beac896fb98663db

## Data integrity and causal construction

- Raw rows: 15,800; valid unique rows in requested interval: 15,800.
- Invalid rows excluded: 0; identical duplicate timestamps removed: 0; out-of-range rows excluded: 0.
- Forward M1 gaps: 17 intervals, 2,898 missing minutes; largest interval 2,881 minutes.
- Warm-up M1 gaps: 17 intervals, 2,901 missing minutes.
- Complete M5 bars from warm-up + forward: 3,137; continuity segments: 27; incomplete UTC-aligned M5 buckets excluded: 31.
- Forward M5 bars: 1,423; forward segments containing at least one forward bar: 15.
- Warm-up rows initialize causal indicators and prior observed completed UTC day/week levels only. No warm-up signal or outcome is scored.
- Signals use completed M5 bars; entry is the immediately next M5 open; settlement is the expiry bar close. Trades crossing the forward-start boundary, a missing M5 bucket, or a continuity-segment boundary are not accepted.

## Candidate results

| Candidate | Side / expiry | N | W/L/D | Decisive WR [95% Wilson] | Wins / all | Net @92% | ROI | PF | Max DD | Longest L streak | Raw signals | Trade freq / M5 | WAIT |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HYD-CAND-001 | PUT / 5m | 0 | 0/0/0 | n/a n/a | n/a | +0.00u | n/a | n/a | 0.00u | 0 | 0 | 0.000% | 100.000% |
| HYD-CAND-008 | PUT / 30m | 5 | 3/2/0 | 60.00% [23.07, 88.24]% | 60.00% | +0.76u | 15.20% | 1.38 | 2.00u | 2 | 6 | 0.351% | 99.649% |
| HYD-CAND-010 | CALL / 60m | 12 | 4/8/0 | 33.33% [13.81, 60.94]% | 33.33% | -4.32u | -36.00% | 0.46 | 5.00u | 5 | 16 | 0.843% | 99.157% |

- Wilson 95% intervals use decisive outcomes (W+L) and assume independent outcomes; serial clustering makes them descriptive, especially at small N.
- Trade frequency is accepted non-overlapping trades divided by complete forward M5 bars; WAIT is its complement. Raw trigger events are shown separately.

### Profit concentration

| Candidate | Top UTC day | Top UTC week |
|---|---|---|
| HYD-CAND-001 | n/a (no positive period net P&L) | n/a (no positive period net P&L) |
| HYD-CAND-008 | 2026-11-16: 100.00% of +1.76u positive period net | 2026-W47: 100.00% of +1.76u positive period net |
| HYD-CAND-010 | 2026-11-13: 100.00% of +0.92u positive period net | n/a (no positive period net P&L) |

### Payout sensitivity (net units)

| Payout | HYD-CAND-001 | HYD-CAND-008 | HYD-CAND-010 |
|---:|---:|---:|---:|
| 50% | +0.00 | -0.50 | -6.00 |
| 60% | +0.00 | -0.20 | -5.60 |
| 70% | +0.00 | +0.10 | -5.20 |
| 80% | +0.00 | +0.40 | -4.80 |
| 85% | +0.00 | +0.55 | -4.60 |
| 90% | +0.00 | +0.70 | -4.40 |
| 92% | +0.00 | +0.76 | -4.32 |
| 95% | +0.00 | +0.85 | -4.20 |
| 100% | +0.00 | +1.00 | -4.00 |

### HYD-CAND-001 — weekly/monthly stability

- Raw forward trigger events: 0; accepted trades: 0; overlap-suppressed events: 0.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 0 | 0/0/0 | n/a | +0.00 |
| 2026-W47 | 0 | 0/0/0 | n/a | +0.00 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 0 | 0/0/0 | n/a | +0.00 |

### HYD-CAND-008 — weekly/monthly stability

- Raw forward trigger events: 6; accepted trades: 5; overlap-suppressed events: 1.
- Boundary-crossing M5 windows purged: 0; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 1 | 0/1/0 | 0.00% | -1.00 |
| 2026-W47 | 4 | 3/1/0 | 75.00% | +1.76 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 5 | 3/2/0 | 60.00% | +0.76 |

### HYD-CAND-010 — weekly/monthly stability

- Raw forward trigger events: 16; accepted trades: 12; overlap-suppressed events: 4.
- Boundary-crossing M5 windows purged: 9; trades excluded after the requested data cutoff: 0.
- Sample status: DESCRIPTIVE_ONLY_INSUFFICIENT_N.

| UTC week | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-W46 | 6 | 3/3/0 | 50.00% | -0.24 |
| 2026-W47 | 6 | 1/5/0 | 16.67% | -4.08 |

| UTC month | N | W/L/D | WR | Net u at 92% |
|---|---:|---|---:|---:|
| 2026-11 | 12 | 4/8/0 | 33.33% | -4.32 |

## Interpretation and limitations

- Minimum sample threshold: 30 new trades per candidate. At least one candidate is below 30 new trades; results are descriptive only.
- No candidate, signal, threshold, direction, expiry, or entry/settlement convention was added or changed.
- Candidates are not pooled into a portfolio; overlap and capital allocation were not preregistered.
- The 92% payout and sensitivity grid are accounting scenarios, not recorded platform payouts.
- Dukascopy EURUSD BID candles are not Pocket Option executable quotes. Spread, quote construction, actual platform payout, latency, and platform settlement rules are not modeled. These results do not establish executable Pocket Option profitability.
- This is prospective observational validation. Do not tune or gate frozen rules using these forward observations.

## Reproducibility

- Workflow run ID: 44038467636
- Workflow URL: https://github.com/Levon4ik026/HydraAI/actions/runs/44038467636
- Machine-readable manifest: manifest.json.
- Trade-level outcomes: trades.csv.
- Validated warm-up, forward-only, combined M1 files, and causal M5 matrix are retained in the workflow artifact.
