# Daily HydraAI research audit — 2026-11-22

Branch under audit: `hydra/research-validation`. All changes recorded by this audit are documentation-only and remain on that branch. No strategy parameters, directions, expiry rules, mathematical-core code, desktop files, `main`, or `hydra/stabilization` were changed.

## Repository state

- Research HEAD before this audit: `93ba65803c7e4f31464de31b882d46e6efb2f8cb`.
- Since the previous checked research HEAD `1916d8bfdf17eb82f2057afacd14a9ade2503343`: two commits; only the forward-validation trigger, manifest and report changed.
- `hydra/stabilization`: `dce8d011ea7f56d7ff890749243ef7d54f0e1afc`.
- `main`: `b5dc96b089073c72619afafa03428827a92dbbf5`.
- Research is 622 commits ahead of stabilization and 0 behind it; research is 713 ahead of main and 6 behind main. Stabilization is 91 ahead of main and 6 behind main (branches diverged).
- PR #1 remains open and Draft. No merge performed.

## Fresh three-candidate forward audit

Workflow [44996799567](https://github.com/Levon4ik026/HydraAI/actions/runs/44996799567) succeeded on code SHA `eafc7d717282de874dbef8401d3c94e5fac74935`. The report was captured 2026-11-22, but the latest completed source candle is still 2026-11-20 21:59 UTC; the weekend produced no new market observations. Therefore this is a successful rerun on the same forward cohort, not a new independent sample.

Source and execution:
- Dukascopy EURUSD M1 BID; forward 2026-11-10 00:00 through 2026-11-20 21:59 UTC.
- 12,819 forward M1 rows; 2,550 complete forward M5 bars; 17 forward continuity segments (29 including warm-up).
- 19 forward gaps, 2,901 missing minutes; largest gap 2,881 minutes; 32 incomplete M5 buckets excluded; no invalid or duplicate rows.
- Warm-up: 8,619 M1 rows, 2026-11-02 through 2026-11-09; no warm-up signal/outcome scored.
- Closed M5 signal; entry next M5 open; expiry bar close; no trade crosses a gap or segment boundary.
- Raw forward CSV SHA-256: `cf10874b0405a3e21fab144d9c1799ad131a10a0e2fc19a6a89affbe353c3f92`.
- Forward M5 feature matrix SHA-256: `7ec5c82659b129b196ae1502d7f0395c120246c2a35a1a59040c1d61b3f4fb31`.

All P&L uses WIN +0.92u, LOSS −1u, DRAW 0u. ROI is net divided by one-unit stakes. Frequency is accepted trades divided by eligible forward M5 bars; WAIT is its complement.

| Candidate | Registered side / expiry | N; W/L/D | WR; 95% Wilson | Wins / all | Net / ROI | PF | Max DD / loss streak | Frequency / WAIT |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CAND-001 | PUT / 5m | 15; 7/8/0 | 46.67%; [24.81, 69.88]% | 46.67% | −1.56u / −10.40% | 0.805 | 3.08u / 2 | 0.588% / 99.412% |
| CAND-008 | PUT / 30m | 6; 4/2/0 | 66.67%; [30.00, 90.32]% | 66.67% | +1.68u / +28.00% | 1.840 | 2.00u / 2 | 0.235% / 99.765% |
| CAND-010 | CALL / 60m | 21; 9/12/0 | 42.86%; [24.47, 63.45]% | 42.86% | −3.72u / −17.71% | 0.690 | 5.32u / 5 | 0.824% / 99.176% |

All three are below the 30-trade descriptive threshold. CAND-008's +1.68u is concentrated: one day accounts for 65.67% of its +2.68u positive-day P&L; its first week was 0/1, second week 4/5. It is not a confirmed edge.

### Paired exact-direction counterfactuals

These are the exact same signal timestamps, entry prices and expiries with only CALL/PUT inverted. They are not new signals and cannot justify changing a frozen direction.

| Candidate | Inverse side | N; W/L/D | WR; 95% Wilson | Net / ROI | PF | Max DD / loss streak |
|---|---|---:|---:|---:|---:|---:|
| CAND-001 | CALL | 15; 8/7/0 | 53.33%; [30.12, 75.19]% | +0.36u / +2.40% | 1.051 | 3.24u / 3 |
| CAND-008 | CALL | 6; 2/4/0 | 33.33%; [9.68, 70.00]% | −2.16u / −36.00% | 0.460 | 4.00u / 4 |
| CAND-010 | PUT | 21; 12/9/0 | 57.14%; [36.55, 75.53]% | +2.04u / +9.71% | 1.227 | 2.16u / 2 |

### Causal CAND-012 re-evaluation

The latest forward artifact's causal M5 matrix was independently replayed against the frozen registry rule: bearish EMA20/EMA50 cross, close below EMA20, registered direction CALL, next M5 open, 5-minute expiry. Freeze timestamp: 2026-11-16 21:50:43 UTC. The matrix contains 4,264 M5 bars overall; after the freeze there were 661 eligible M5 opportunities through 2026-11-20 and 6 signals.

- Registered CALL: 6 trades, 1/5/0; WR 16.67%, Wilson 95% [3.01, 56.35]%; net −4.08u; ROI −68.00%; PF 0.184; max DD 5.00u; max loss streak 5; frequency 0.908%; WAIT 99.092%.
- Exact same-event PUT counterfactual: 6 trades, 5/1/0; WR 83.33%, Wilson 95% [43.65, 96.99]%; net +3.60u; ROI +60.00%; PF 4.600; max DD 1.00u; max loss streak 1.
- The inverse is a six-event paired counterfactual, not independent validation. Do not flip CAND-012 based on this sample.

### Always-direction baselines on the same forward M5 opportunities

One non-overlapping position per horizon and continuity segment; next M5 open, settlement at the corresponding expiry-bar close.

| Expiry | Side | N; W/L/D | WR; 95% Wilson | Net / ROI | PF | Max DD / loss streak | Frequency / WAIT |
|---|---|---:|---:|---:|---:|---:|---:|
| 5m | CALL | 2,533; 1,167/1,295/71 | 47.40%; [45.43, 49.38]% | −221.36u / −8.74% | 0.829 | 241.44u / 11 | 100% / 0% |
| 5m | PUT | 2,533; 1,295/1,167/71 | 52.60%; [50.62, 54.57]% | +24.40u / +0.96% | 1.021 | 26.32u / 9 | 100% / 0% |
| 30m | CALL | 415; 185/228/2 | 44.79%; [40.07, 49.62]% | −57.80u / −13.93% | 0.746 | 58.64u / 8 | 16.918% / 83.082% |
| 30m | PUT | 415; 228/185/2 | 55.21%; [50.38, 59.93]% | +24.76u / +5.97% | 1.134 | 12.56u / 8 | 16.918% / 83.082% |
| 60m | CALL | 202; 94/106/2 | 47.00%; [40.20, 53.91]% | −19.52u / −9.66% | 0.816 | 24.04u / 6 | 8.556% / 91.444% |
| 60m | PUT | 202; 106/94/2 | 53.00%; [46.09, 59.80]% | +3.52u / +1.74% | 1.037 | 8.56u / 5 | 8.556% / 91.444% |

The forward period had a broad PUT directional bias. Candidate filters must be judged against these same-side baselines, not only against zero. Wilson intervals are descriptive and assume independent decisive outcomes; serial clustering and the small candidate samples limit inference.

## CAND-014 latest forward status

The last successful official NY audit is [44898827380](https://github.com/Levon4ik026/HydraAI/actions/runs/44898827380), captured 2026-11-21, source through 2026-11-20 21:59 UTC. Frozen rule unchanged: completed 18:00–16:59 America/New_York session, >=99% coverage, no gap >5 minutes, 20 preceding valid sessions, session log return <= −1.0 times the preceding-20 mean absolute log return; CALL at next 18:00 NY open; fixed 30-minute expiry.

- 1 forward CALL trade, 0/1/0; WR 0.00%, Wilson 95% [0.00, 79.35]%; net −1.00u; ROI −100%; PF 0; max DD 1.00u; max loss streak 1.
- Matched PUT: 1/0/0, +0.92u.
- Source: 1,036,990 valid unique M1 rows; 581 valid NY sessions; 118 raw shock matches.
- Promotion gate remains at least 100 forward CALL trades. One trade is not evidence. No new completed NY session was available in the 2026-11-22 weekend refresh.

The stale registry statement “forward N=0” was corrected to the latest confirmed one-trade result. The preregistration execution log now records the weekend refresh; no rule or gate changed.

## Additional locked forward audit

Latest successful [locked audit 44996803560](https://github.com/Levon4ik026/HydraAI/actions/runs/44996803560), source through 2026-11-20 21:59 UTC; 1,076,077 valid M1 rows, 212,774 complete M5 bars, 2,670 segments. Frozen prior-only z-score; bearish close below previous close; next M5 open; 15-minute expiry; one position at a time per candidate/segment.

| Hypothesis | Side | N; W/L/D | WR; 95% Wilson | Net / ROI | PF | Max DD / streak | Daily bootstrap 95% CI |
|---|---|---:|---:|---:|---:|---:|---:|
| MEAN_REV_20_Z2.0 | PUT | 51; 27/24/0 | 52.94%; [39.52, 65.95]% | +0.84u / +1.65% | 1.035 | 5.32u / 5 | [−13.48, +15.36]u |
| MEAN_REV_40_Z2.0 | PUT | 40; 18/22/0 | 45.00%; [30.71, 60.17]% | −5.44u / −13.60% | 0.753 | 6.40u / 5 | [−15.76, +3.64]u |

MEAN_REV_20 has only 54.7% bootstrap probability of positive net; its interval spans zero. MEAN_REV_40 has 13.5%. Neither is qualified.

## Updated multi-year research

Latest successful long-history job is included in [Research validation run 44996803564](https://github.com/Levon4ik026/HydraAI/actions/runs/44996803564), artifact captured 2026-11-22 07:11 UTC. Source SHA-256 `b2034dda5a9dc06fde044dc8170f1620dfaf9a766a876f1eecc1f8112524d71d`; 1,076,077 valid M1 rows, 212,774 complete M5 bars, 2,670 segments; coverage 2024-01-01 22:00 to 2026-11-20 21:59 UTC. Splits: TRAIN before 2025-09-17; VALIDATION 2025-09-17 through 2026-04-13; TEST from 2026-04-14. TEST is chronological but previously explored, not an untouched independent holdout.

- Standalone screen: 20 families × 6 expiries = 120 variants, 360 split rows. No variant had positive net in TRAIN, VALIDATION and TEST simultaneously.
- Best VALIDATION point estimate in the screen: MEAN_REV_20_Z2.0_PUT, 10m: TRAIN 2,404 trades, 1,233/1,138/33, WR 52.00%, net −3.64u; VALIDATION 804, 431/366/7, WR 54.08%, Wilson [50.61,57.51]%, net +30.52u; TEST 863, 454/397/12, WR 53.35%, Wilson [49.99,56.68]%, net +20.68u. It fails the TRAIN positive-net gate and its TEST lower bound is below break-even.
- Best-looking TEST row ENGULF_PUT 60m: TEST 1,450, 796/645/9, WR 55.24%, net +87.32u, PF 1.14; but TRAIN net −175.12u and VALIDATION net −58.44u. It is not a candidate.
- Exact inverse MOM_BREAK_12_CALL -> PUT, 15m: TRAIN 4,618, 2,384/2,189/45, WR 52.13%, +4.28u; VALIDATION 1,531, 827/686/18, WR 54.66%, +74.84u; TEST 1,500, 780/706/14, WR 52.49%, Wilson [49.95,55.02]%, +11.60u, PF 1.02, DD 36.64u, longest loss streak 8. TEST daily bootstrap 95% net interval [−59.40,+80.24]u, P(net>0)=62.3%; 2026-Q4 TEST was 194/189/3, WR 50.65%, net −10.52u.
- Multi-feature regime screen: 68 TRAIN-frozen context rules. Aggregate TEST net was −39.28u for trend×volatility, −34.08u for trend×location, +24.68u for volatility×location; aggregate rows can double-count timestamps and are not executable portfolios. No adaptive rule is promoted.

## CI and repository issues

- Research push run 44996799567: SUCCESS.
- On the previous executable code SHA `eafc7d7`, research tests run 44996803564, math core run 44996803561 and locked audit run 44996803560 all succeeded.
- PR checks on the report-only HEAD `93ba6580` (runs 44996825723, 44996825697, 44996825617) show `action_required` with zero jobs, not failed test jobs. The prior executable SHA had successful PR checks.
- Stabilization has no current run; latest successful Math core run 42376660469 on 2026-11-07. Main and stabilization have diverged (main is 6 commits ahead, stabilization 91 commits ahead).
- No new failure was found on research-validation. No CI result is being treated as a backtest result.

## Separate DEMO integration branch review — no changes made there

Branch `hydra/demo-execution-v1-20261121` HEAD `0a182dd8645cafb8c582bec47e718387b5f49774`, 27 commits ahead of stabilization, 0 behind. It contains an experimental desktop patch and an actual DEMO execution worker; it is not integrated into the user's local project or merged into stabilization.

- CI runs 44938736159 and 44938741833 failed. Compile passed; 6 of 7 tests passed. The failing assertion expects “not VERIFIED” for a PENDING verification record, but `verification_rejection()` first returns “missing or invalid verification timestamp”. Safe minimal fix: check the status field before parsing the timestamp, retaining rejection in both cases. No change was made to this branch.
- Critical strategy parity defects: runtime emits CAND-008 as CALL although the registry freezes inverse PUT; emits CAND-010 as PUT although the registry freezes inverse CALL; emits CAND-012 as PUT although the registry freezes inverse CALL. CAND-001 also adds EMA20>EMA50 and ATR-rank>67 conditions beyond the frozen base RSI14>=70 bearish M5 rule. These must be corrected or explicitly preregistered as distinct variants before any integration.
- Adaptive selector is fail-closed: it requires at least 100 forward trades per regime, positive expectancy and a 95% Wilson lower bound above break-even; with current samples it should return WAIT. The branch also contains an explicit GUI path to enable DEMO auto-execution. It was not run; no broker connection or order was made.
- Broker-expiry filtering blocks candidates whose 30m/60m expiries are not actually advertised. The README notes a previous metadata observation of [60,120,180,300] seconds, which would leave only 5m candidates eligible; this must be checked against fresh live metadata before any DEMO integration.
- The separate `hydra/desktop-demo-integration` branch is 91 commits behind stabilization and diverged; do not use it as the integration base.

## Decision and next step

No candidate is confirmed profitable; the five-candidate forward sample is descriptive and underpowered. Do not change CALL/PUT, expiry or regime thresholds based on the paired counterfactuals. Next research step: keep the frozen rules unchanged, continue forward logging, and prepare an isolated shadow-only integration after strategy parity and DEMO expiry support are verified. No live or automatic execution is authorized by this audit.
