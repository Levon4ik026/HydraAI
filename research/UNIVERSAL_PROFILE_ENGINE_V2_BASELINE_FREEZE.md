# Candidate cohort baseline v2 — current frozen EURUSD snapshot

Date frozen: 2026-11-12  
Branch: `hydra/research-validation`  
Config: `candidate_profile_config_v2.json`  
Prior baseline preserved unchanged: `candidate_profile_config_v1.json`  
Source dataset SHA-256: `4a084d3af598342e2b55e52bb79558825797c64410b875ff8e83ec019972decd`  
Feature matrix SHA-256: `7b5640aab878e740e05c5f9b9c856e6b696f45d040c856984bb6800b2c5b1576`  
M1 rows: 1,061,819; complete M5 rows: 209,936; gap-separated segments: 2,653.  
Snapshot ID: `EURUSD_M1_BID_DUKASCOPY_2024-01-01_to_2026-11-09_capture_2026-11-12_v1`.

## Why v2 exists

The v1 registry contains historical cohort counts from a prior raw-data snapshot that is no longer available byte-for-byte. The current pinned snapshot was reprocessed using the frozen candidate definitions. Four candidates matched TRAIN and VALIDATION but had TEST-only count differences. A timestamp-level audit then compared the legacy event builders and universal engine on the same current M5 segments. All four passed accepted-event timestamp, non-overlap schedule, and outcome parity.

Therefore v2 freezes the observed current-snapshot cohort counts as a **new baseline**. It does not rewrite, supersede, or claim to reproduce the unavailable v1 source snapshot.

## Current-snapshot cohort counts

Counts below are in W/L/D order. Each candidate's complete TRAIN / VALIDATION / TEST values are frozen in `candidate_profile_config_v2.json`.

| Candidate | TRAIN W/L/D | VALIDATION W/L/D | TEST W/L/D |
|---|---:|---:|---:|
| HYD-CAND-001 | 401/323/11 | 110/80/2 | 124/94/1 |
| HYD-CAND-008 | 130/97/0 | 25/20/0 | 47/29/0 |
| HYD-CAND-003 | 967/910/10 | 345/253/8 | 289/255/5 |
| HYD-CAND-006 | 381/380/3 | 150/107/1 | 131/133/3 |
| HYD-CAND-007 | 286/275/4 | 113/79/1 | 92/99/1 |
| HYD-CAND-010 | 301/274/3 | 116/85/1 | 107/89/2 |
| HYD-CAND-012 | 321/293/13 | 132/93/4 | 103/86/5 |
| HYD-CAND-013 | 644/560/11 | 236/141/3 | 228/207/8 |
| HYD-CAND-011 | 782/781/10 | 273/210/7 | 307/285/6 |
| HYD-CAND-009 | 89/85/1 | 21/16/0 | 39/23/1 |

## Parity audit interpretation

Workflow run [43211654625](https://github.com/Levon4ik026/HydraAI/actions/runs/43211654625) completed the legacy-vs-universal parity audit with zero candidate failures.

- HYD-CAND-001, HYD-CAND-011, and HYD-CAND-012: legacy and universal raw eligible trigger timestamps, accepted schedules, and W/L/D outcomes agree.
- HYD-CAND-013: the legacy builder emitted 2,271 pre-guard events while the universal engine emitted 2,241; after applying the same frozen eligibility guards and split rules, eligible trigger timestamps, accepted schedules (2,038), and outcomes agree. This pre-guard count difference is retained as an audit note rather than hidden.
- The audit proves implementation parity on this current snapshot, not parity with the unavailable old raw CSV.

## Research guardrails

1. v1 remains immutable historical provenance; v2 is a separate source-snapshot baseline.
2. A v2 cohort gate passing means exact reproduction of this snapshot's counts, not evidence of profitability.
3. The historical TEST period has prior exploratory exposure and is not pristine independent confirmation.
4. No regime filter is promoted from the descriptive profiles without predeclared validation and appropriate uncertainty controls.
5. Background comparisons in the current profile engine are overlapping eligible bars, not matched non-overlap controls. Do not treat those lifts as inferential evidence.
6. Dukascopy BID M1/M5 is a historical proxy, not Pocket Option executable pricing. The 92% payout remains a scenario assumption.

## Next stage

Use the frozen v2 baseline for reproducible profiling. Upgrade the control comparison to deterministic matched controls, report calendar-day block-bootstrap uncertainty for predeclared candidate/regime combinations, and preserve TRAIN/VALIDATION separation. Do not use TEST to choose filters. Prospective validation on the actual Pocket Option feed and realized payout remains required.
