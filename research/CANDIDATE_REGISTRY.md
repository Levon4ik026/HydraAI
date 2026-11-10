# HydraAI Research Lab — Candidate Registry

**Branch:** `hydra/research-validation`  
**Charter:** `docs/RESEARCH_LAB_CHARTER.md`  
**Purpose:** inventory of promising strategy candidates found during discovery. This is not the confirmed strategy catalog. Every candidate remains isolated from production.

## Registry rules

- Add every promising candidate with its exact signal definition, timeframe, expiry, data source, split results, sample size, payout assumption, report/code links, and limitations.
- Preserve historical candidates even when evidence is incomplete; mark missing fields explicitly rather than guessing.
- Candidate discovery comes first. After the candidate list is sufficiently broad, investigate the market state and concrete market situation for each candidate separately.
- Target discovery threshold: decisive win rate around **57% or higher**. Results below that may remain in the registry when they are historically notable or useful for further research, but must be clearly qualified.
- No candidate is confirmed merely by a high win rate. Require independent periods, adequate sample, control cohorts, uncertainty/dependence checks, and realistic payout/quote validation.

## Candidate index

| ID | Candidate | Signal / family | Direction | Expiry | Best reported result | Status |
|---|---|---|---|---:|---|---|
| HYD-CAND-001 | RSI14-70 bearish reversal | M5 RSI(14) >= 70 and bearish signal candle | PUT | 5m | TEST 57.14% (n=218); VALIDATION 57.89% (n=192) | Candidate — priority |
| HYD-CAND-002 | MIXED efficiency regime | Market filter/classifier based on price-movement efficiency over the previous 15 candles; exact entry logic not recovered | Unknown | 10m | 64.77% (57W/31L/1D, n=89) | Candidate — archival, incomplete |
| HYD-CAND-006 | Previous-day high sweep/reclaim inverse | Previous observed UTC day high swept, M5 bearish candle closes back below | CALL (inverse) | 10m | VALIDATION 58.37% (n=258), TEST 49.62% (n=267) | Archived exploratory — unstable |
| HYD-CAND-007 | Previous-day high sweep/reclaim inverse | Previous observed UTC day high swept, M5 bearish candle closes back below | CALL (inverse) | 30m | VALIDATION 58.85% (n=193), TEST 48.17% (n=192) | Archived exploratory — unstable |
| HYD-CAND-008 | Previous-week low sweep/reclaim inverse | Previous completed UTC week low swept, M5 bullish candle closes back above | PUT (inverse) | 30m | TRAIN 57.27%; TEST 61.84% (n=76); VALIDATION 55.56% (n=45) | Candidate — priority for further research |
| HYD-CAND-009 | Previous-week low sweep/reclaim inverse | Previous completed UTC week low swept, M5 bullish candle closes back above | PUT (inverse) | 60m | TEST 62.90% (n=63); VALIDATION 56.76% (n=37) | Exploratory inverse lead — low sample / borderline validation |
| HYD-CAND-010 | Previous-day low close breakout, inverse CALL, 60m | Previous observed completed UTC day low close breakout | CALL (inverse) | 60m | VALIDATION 57.71% (n=202); TEST 54.59% (n=198) | Exploratory candidate lead — consistency not yet established |
| HYD-CAND-011 | Up-shock second-bar reversal | Prior >=2x median-TR upward shock; second bar reverses | PUT | 15m | VALIDATION 56.52% (n=490); TEST 52.04% (n=594) | Exploratory lead — split instability |

| HYD-CAND-012 | Bearish EMA20/EMA50 cross, inverted CALL | Fresh EMA20 cross below EMA50 with close below EMA20; exact-event inverse | CALL (inverse) | 5m | VALIDATION 58.67% (n=229); TEST 54.26% (n=193); positive net all splits | Exploratory lead — inverse direction; not confirmed |
---

## HYD-CAND-001 — RSI14-70 bearish reversal, PUT, 5m

- **Status:** Candidate; not confirmed.
- **Discovery experiment:** clean-slate expanded strategy screen.
- **Data:** Dukascopy EUR/USD M1 BID, 2024-01-01 through 2026-11-08; 1,061,814 valid M1 rows; complete M5 bars derived from this feed (209,933 bars). Source is not identical to Pocket Option quotes.
- **Signal definition:** on a closed M5 candle, RSI(14) >= 70 AND the candle is bearish (`close < open`) → PUT. This is a level condition, not an RSI cross-back below 70. Entry at the next M5 candle open; expiry at the close of the fifth subsequent M5 candle (5 minutes).
- **Non-overlap:** one active trade per strategy/expiry within each continuous data segment.
- **Payout accounting:** assumed 92%; win +0.92u, loss -1u, draw 0u. Break-even decisive WR 52.0833%. Actual Pocket Option payout was not available per trade.

| Split | Trades | W / L / D | Decisive WR | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 735 | 401 / 323 / 11 | 55.39% | +45.92 | 19.16 | 7 |
| VALIDATION | 192 | 110 / 80 / 2 | 57.89% | +21.20 | 6.96 | 5 |
| TEST | 218 | 124 / 93 / 1 | 57.14% | +21.08 | 8.32 | 6 |

- **Uncertainty:** reported Wilson 95% CI: VALIDATION [50.79%, 64.69%], TEST [50.49%, 63.55%]. These intervals do not account for serial dependence; effective uncertainty may be wider.
- **Split dates:** TRAIN before 2025-09-17; VALIDATION 2025-09-17 through 2026-04-13; TEST from 2026-04-14 onward. Boundary-crossing outcomes were purged.
- **Why retained:** validation and test both exceed the 57% discovery target, with positive assumed-payout net results; train is lower at 55.39%, so this is not yet robustly established.
- **Known limitations:** multiple strategy/expiry combinations were screened; no matched control cohort yet; no block bootstrap yet; assumed fixed payout; Dukascopy BID differs from Pocket Option feed; no platform spread/latency execution model. RSI candidate metrics are not affected by the separate MACD initialization defect identified in the expanded script.
- **Next research step:** continue candidate discovery first, as requested. Later characterize this candidate's own market situation and compare it against matched controls/analogs without tuning on TEST.
- **Report:** `hydra-expanded-strategy-discovery` artifact from workflow run `42722101824`.
- **Workflow:** https://github.com/Levon4ik026/HydraAI/actions/runs/42722101824
- **Screen code:** https://github.com/Levon4ik026/HydraAI/blob/hydra/research-validation/research/expanded_strategy_screen.py
- **Discovery commit:** `1b0a4a11b209791833594d8c10ffecf4426d4c07`

## HYD-CAND-002 — MIXED efficiency regime, 10m

- **Status:** Candidate — archival and incomplete; do not treat as confirmed or as a verified 80% result.
- **Historical result recovered from prior research discussion:** 57 wins, 31 losses, 1 draw; **64.77% decisive win rate** over 89 trades; 10-minute expiry; reported net +21.44u under an assumed 92% payout.
- **Frequency noted at the time:** 89 trades across 208 calendar days (about 0.43 trades/day, approximately 3/week). Low frequency and modest sample size.
- **Known concept:** a MIXED market-regime classification based on price-movement efficiency over the previous 15 candles.
- **Not recovered / unknown:** exact timeframe of the 15-candle efficiency calculation; formula and thresholds; exact entry trigger and CALL/PUT direction rules; signal timestamp convention; data source and exact tested date range; split structure; trade-level events; draw handling details; code/report/commit artifact. These must be recovered before a reproducible rerun.
- **Interpretation:** the available historical note supports 64.77%, not ~80%. No evidence retrieved so far substantiates an 80% MIXED result. There may have been a different test or candidate; do not merge it with this record without source evidence.
- **Next action:** locate the original MIXED experiment or reconstruct it only after its exact rules and data cohort are recovered. Then rerun as a separately versioned experiment, preserving the original definition before any changes.
- **Prior discussion:** 2026-11-08; no dedicated GitHub artifact or exact entry-direction rules were recorded in the retrieved history.

---

## Discovery queue

New candidates are appended here as separate cards. Do not begin market-situation profiling until the broad candidate-discovery pass is complete or the user explicitly changes the order. Candidate IDs are permanent; revisions should add dated notes rather than silently rewriting historical results.


## Обязательная ветка проверки инверсии

Слабые кандидаты не отбрасываются автоматически. Для каждого перспективного кандидата с низким или отрицательным результатом необходимо проверить вариант с противоположным направлением сделки при неизменных условиях сигнала, тайминге входа, экспирации и фильтрах.

- Исходный и инвертированный варианты тестируются на одних и тех же сигнальных событиях и временных выборках.
- Меняется только CALL ↔ PUT. Нельзя одновременно менять пороги, экспирацию или фильтры.
- W/L/D и чистый результат фиксируются отдельно для обоих вариантов на TRAIN / VALIDATION / TEST.
- Инверсия, прошедшая первичный отбор, получает отдельный постоянный ID и отдельную карточку; исходная запись сохраняется.
- Нельзя выбирать инверсию по TEST и затем использовать тот же TEST как независимое подтверждение.
- Инверсия не гарантирует прибыльность: учитываются выплата, ничьи, просадка, выборка и отличие исторических котировок от исполнения Pocket Option.

Это правило применяется и к новым исследованиям, и к повторной проверке уже зарегистрированных кандидатов.


## HYD-CAND-003 — Donchian50 breakout fade, PUT, 20m (inverse-direction lead)

- **Status:** Preliminary inverse hypothesis; not confirmed and not yet promoted to a robust candidate.
- **Origin:** Inversion of the exact event set for DONCHIAN50_BREAK_CALL from the second-wave discovery screen. The original trigger is a closed M5 bullish candle whose close exceeds the highest high of the preceding 50 completed M5 candles.
- **Inverse rule:** Keep every original trigger timestamp, entry timing, expiry, and non-overlap decision unchanged; replace CALL with PUT. Entry is at the next M5 open; expiry is the close of the fourth subsequent M5 candle (20 minutes).
- **Data:** Same Dukascopy EUR/USD M1 BID history and chronological split as second-wave screen; assumed payout 92%; win +0.92u, loss -1u, draw 0u.
- **Corrected inverse results:** Calculated from the exact original signal events within their own continuous source segments; the first inverse patch had a stale-segment defect and its run is explicitly excluded. Corrected workflow run 42724247482 succeeded on commit 47271bd4008ad4c77a606b1f0f1d02c88cb8e14.

| Split | Trades | Inverse W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,887 | 967 / 910 / 10 | 51.52% | [49.26, 53.77]% | -20.36 | 48.32 | 11 |
| VALIDATION | 606 | 345 / 253 / 8 | 57.69% | [53.70, 61.59]% | +64.40 | 11.96 | 6 |
| TEST | 549 | 289 / 255 / 5 | 53.12% | [48.92, 57.28]% | +10.88 | 21.96 | 8 |

- **Interpretation:** Validation clears the 57% discovery threshold with a substantial sample. TEST remains above the assumed-payout break-even rate and positive in net, but falls to 53.12%; TRAIN is also below break-even at 51.52%. The validation-to-test decline means this is a research lead, not a stable/confirmed strategy. The corrected TEST cohort contains 549 trades (not the earlier provisional 547).
- **Uncertainty:** Wilson intervals are shown above but assume independent outcomes and do not account for serial dependence. No block-bootstrap or matched-control test yet. Multiple-testing bias remains.
- **Important:** The result is Dukascopy BID, not executable Pocket Option quotes; payout is assumed 92%, with no spread/latency model.
- **Code / report:** research/second_wave_strategy_screen.py; corrected report artifact from workflow run 42724247482.


## HYD-CAND-004 — ATR expansion fade, CALL, 20m (inverse-direction lead)

- **Status:** Candidate lead for further validation; not confirmed.
- **Origin signal:** ATR(14) expands above 1.25 × its prior value and the closed M5 candle is bearish with body size at least 0.5 × ATR. Original event direction is PUT.
- **Inverse rule:** CALL on the exact same bearish ATR-expansion events; no changes to signal timestamp, entry, expiry, split or non-overlap. Entry next M5 open; expiry at close of the fourth subsequent M5 candle (20m).
- **Data / accounting:** Dukascopy EUR/USD M1 BID, 2024-01-01 to 2026-11-08; 92% assumed payout (+0.92u/-1u/0u). Not Pocket Option executable pricing.
- **Exact-event inversion audit:** workflow run 42726660593; artifact `hydra-first-wave-inversion-audit`; code `research/first_wave_inversion_screen.py`.

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 342 | 184 / 155 / 3 | 54.28% | [48.96, 59.50]% | +14.28 | 19.28 | 8 |
| VALIDATION | 92 | 51 / 40 / 1 | 56.04% | [45.81, 65.79]% | +6.92 | 7.24 | 5 |
| TEST | 109 | 62 / 46 / 1 | 57.41% | [47.99, 66.32]% | +11.04 | 7.56 | 4 |

- **Interpretation:** positive payout-adjusted net in all three chronological splits; WR increases from 54.28% TRAIN to 56.04% VALIDATION and 57.41% TEST. This is the most directionally consistent inverse lead in this first-wave audit, but validation/test samples are modest and Wilson intervals are wide. The 57.41% TEST result is descriptive, not a parameter-selection target. Requires new independent period / forward validation and dependence-aware uncertainty.
- **Limitations:** broad multi-family/multi-expiry discovery creates multiple-testing bias; no matched control or block bootstrap yet; assumed payout and BID-vs-platform mismatch remain. Keep separate from the original ATR_EXPANSION_PUT strategy.

## HYD-CAND-005 — Inside-bar breakout fade, CALL, 30m (inverse-direction lead)

- **Status:** Candidate lead; not confirmed.
- **Origin signal:** On closed M5 bars, the prior candle is inside its mother candle (`high[i-1] < high[i-2]` and `low[i-1] > low[i-2]`); current candle closes below the mother candle low and is bearish. Original event direction is PUT.
- **Inverse rule:** CALL on the exact same downside-break events. Entry next M5 open; expiry at close of the sixth subsequent M5 candle (30m). All event timestamps and non-overlap choices are shared by original/inverse variants.
- **Data / accounting:** same Dukascopy EUR/USD M1 BID history and 92% assumed payout as HYD-CAND-004.
- **Exact-event inversion audit:** workflow run 42726660593; artifact `hydra-first-wave-inversion-audit`.

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,500 | 774 / 715 / 11 | 51.98% | [49.44, 54.51]% | -2.92 | 49.64 | 13 |
| VALIDATION | 483 | 276 / 204 / 3 | 57.50% | [53.04, 61.85]% | +49.92 | 9.72 | 6 |
| TEST | 489 | 259 / 223 / 7 | 53.73% | [49.27, 58.14]% | +15.28 | 13.88 | 11 |

- **Interpretation:** Validation reaches 57.50% with a substantial sample and positive net; TEST remains positive at 53.73%, but TRAIN is near break-even and the max loss streak in TEST is 11. Interesting inverse lead, but not robust enough for confirmation.
- **Limitations:** same discovery-wide multiple-testing, serial dependence, assumed payout and BID-vs-platform limitations. Requires independent replication and matched control.


## HYD-CAND-006 — Previous-day high sweep/reclaim, inverse CALL, 10m

- **Status:** Archived exploratory inverse lead; not promoted and not confirmed.
- **Source event:** On a closed M5 bearish candle, price trades above the previous observed UTC trading day's completed high and closes back below it. Original direction is PUT; inverse direction is CALL on the exact same event timestamps.
- **Execution:** Entry at next M5 open; expiry at close of the second subsequent M5 candle (10m). Original/inverse share the same events and non-overlap schedule.
- **Data / accounting:** Dukascopy EUR/USD M1 BID, 2024-01-01 through 2026-11-08; assumed payout 92% (+0.92u/-1u/0u).
- **Results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 764 | 381 / 380 / 3 | 50.07% | [46.52, 53.61]% | -29.48 | 55.40 | 9 |
| VALIDATION | 258 | 150 / 107 / 1 | 58.37% | [52.26, 64.23]% | +31.00 | 11.48 | 7 |
| TEST | 267 | 131 / 133 / 3 | 49.62% | [43.64, 55.61]% | -12.48 | 17.16 | 5 |

- **Interpretation:** Validation exceeds the discovery threshold with a positive assumed-payout net, but TRAIN is near 50% and TEST falls below break-even with negative net. Clear instability; retain only as a historical inverse lead.
- **Limitations:** Discovery-wide multiple testing, serial dependence, no matched control or dependence-aware interval; BID feed differs from Pocket Option executable quotes; payout fixed at 92%.
- **Report / workflow:** [Fourth-wave discovery report artifact](https://github.com/Levon4ik026/HydraAI/actions/runs/42798893511), run 42798893511.
- **Code:** research/fourth_wave_sweep_reclaim_screen.py.

## HYD-CAND-007 — Previous-day high sweep/reclaim, inverse CALL, 30m

- **Status:** Archived exploratory inverse lead; not promoted and not confirmed.
- **Source event:** Same previous-observed-UTC-day high sweep/reclaim bearish M5 event as HYD-CAND-006. Original direction PUT; inverse CALL.
- **Execution:** Entry next M5 open; expiry at close of the sixth subsequent M5 candle (30m); identical event timestamps and non-overlap schedule for both directions.
- **Data / accounting:** Same Dukascopy EUR/USD M1 BID history and 92% assumed payout as HYD-CAND-006.
- **Results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 565 | 286 / 275 / 4 | 50.98% | [46.85, 55.10]% | -11.88 | 32.96 | 8 |
| VALIDATION | 193 | 113 / 79 / 1 | 58.85% | [51.79, 65.57]% | +24.96 | 7.52 | 4 |
| TEST | 192 | 92 / 99 / 1 | 48.17% | [41.19, 55.22]% | -14.36 | 18.96 | 7 |

- **Interpretation:** Strong-looking validation is contradicted by both TRAIN and TEST; TEST net is negative. Do not promote.
- **Limitations / provenance:** Same as HYD-CAND-006; exact same event family with a different predeclared expiry, not independent evidence.
- **Report / workflow:** [Fourth-wave discovery report artifact](https://github.com/Levon4ik026/HydraAI/actions/runs/42798893511), run 42798893511.
- **Code:** research/fourth_wave_sweep_reclaim_screen.py.

## HYD-CAND-008 — Previous-week low sweep/reclaim, inverse PUT, 30m

- **Status:** Candidate — priority for further research; not confirmed. VALIDATION is currently 55.56%, below the 57% discovery target, but the candidate is retained because TRAIN is 57.27% and the untouched TEST is 61.84%. The small validation sample (n=45) makes the estimate uncertain. Any improvement work must be developed on TRAIN or a newly designated development cohort; do not repeatedly tune against this same VALIDATION or use TEST for selection.
- **Source event:** On a closed M5 bullish candle, price trades below the previous completed UTC week's low and closes back above it. Original direction is CALL; inverse direction is PUT on the exact same event timestamps.
- **Execution:** Entry next M5 open; expiry at close of the sixth subsequent M5 candle (30m); original/inverse share identical events and non-overlap schedule.
- **Data / accounting:** Dukascopy EUR/USD M1 BID, 2024-01-01 through 2026-11-08; assumed payout 92% (+0.92u/-1u/0u).
- **Results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 227 | 130 / 97 / 0 | 57.27% | [50.77, 63.53]% | +22.60 | 8.80 | 5 |
| VALIDATION | 45 | 25 / 20 / 0 | 55.56% | [41.18, 69.06]% | +3.00 | 3.56 | 3 |
| TEST | 76 | 47 / 29 / 0 | 61.84% | [50.60, 71.94]% | +14.24 | 5.00 | 5 |

- **Interpretation:** TRAIN and TEST are encouraging, but VALIDATION is below threshold and small (45 trades). TEST must not be used to promote or tune this candidate. Retain for later independent analog-period study only.
- **Limitations:** Weekly-level family is sparse; confidence intervals are wide; serial dependence and multiple-testing effects unmodeled; BID feed and fixed payout do not reproduce Pocket Option execution.
- **Report / workflow:** [Fourth-wave discovery report artifact](https://github.com/Levon4ik026/HydraAI/actions/runs/42798893511), run 42798893511.
- **Code:** research/fourth_wave_sweep_reclaim_screen.py.

## HYD-CAND-009 — Previous-week low sweep/reclaim, inverse PUT, 60m

- **Status:** Exploratory inverse lead; not confirmed; validation is borderline and sample is very small.
- **Source event:** Same previous-completed-UTC-week low sweep/reclaim bullish M5 event as HYD-CAND-008. Original direction CALL; inverse PUT.
- **Execution:** Entry next M5 open; expiry at close of the twelfth subsequent M5 candle (60m); identical event timestamps and non-overlap schedule for both directions.
- **Data / accounting:** Same Dukascopy EUR/USD M1 BID history and 92% assumed payout as HYD-CAND-008.
- **Results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 175 | 89 / 85 / 1 | 51.15% | [43.78, 58.47]% | -3.12 | 8.28 | 4 |
| VALIDATION | 37 | 21 / 16 / 0 | 56.76% | [40.91, 71.33]% | +3.32 | 3.32 | 2 |
| TEST | 63 | 39 / 23 / 1 | 62.90% | [50.46, 73.84]% | +12.88 | 3.08 | 3 |

- **Interpretation:** TEST is high but cannot be used for selection; VALIDATION is just below threshold with only 37 trades and a wide interval, while TRAIN is close to break-even. Keep as a low-sample exploratory lead only.
- **Limitations:** Weekly-level family is sparse; confidence intervals are wide; serial dependence and multiple-testing effects unmodeled; BID feed and fixed payout do not reproduce Pocket Option execution.
- **Report / workflow:** [Fourth-wave discovery report artifact](https://github.com/Levon4ik026/HydraAI/actions/runs/42798893511), run 42798893511.
- **Code:** research/fourth_wave_sweep_reclaim_screen.py.


## HYD-CAND-010 — Previous-day low close breakout, inverse CALL, 60m

- **Status:** Exploratory candidate lead; not confirmed. VALIDATION clears the 57% discovery threshold (57.71%, n=202) and all three chronological splits have positive assumed-payout net, but TRAIN is only 52.35% and TEST is 54.59%. This is a consistency lead for independent replication, not a promoted strategy.
- **Source event:** On a closed M5 candle, the close crosses below the immediately preceding observed completed UTC day's low, with the prior M5 close at or above that level. Original event direction is PUT. The inverse candidate is CALL on the exact same event timestamps.
- **Execution:** Entry at next M5 open; expiry at close of the twelfth subsequent M5 candle (60m). Original/inverse share identical events and non-overlap schedule.
- **Data / accounting:** Dukascopy EUR/USD M1 BID, 2024-01-01 through 2026-11-08; assumed payout 92% (+0.92u/-1u/0u). Chronological splits and boundary purging as specified in the sixth-wave report.
- **Results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) | Max loss streak |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 578 | 301 / 274 / 3 | 52.35% | [48.26, 56.40]% | +2.92 | 31.40 | 7 |
| VALIDATION | 202 | 116 / 85 / 1 | 57.71% | [50.80, 64.33]% | +21.72 | 8.08 | 8 |
| TEST | 198 | 107 / 89 / 2 | 54.59% | [47.60, 61.41]% | +9.44 | 13.04 | 6 |

- **Interpretation:** This is the most consistent sixth-wave lead among the validation-threshold results: positive net in TRAIN, VALIDATION and TEST, with validation above 57%. However, TRAIN is only marginally above the 92%-payout break-even rate, TEST is below the 57% target, and all Wilson intervals include materially weaker performance. It remains exploratory and needs a new independent period / prospective quote-level replication. Do not tune against this VALIDATION or TEST.
- **Limitations:** Sixth-wave screen tested 14 event families × 6 expiries × 2 directions; substantial multiple-testing exposure and serial dependence remain. Wilson intervals do not correct either. Dukascopy BID is not Pocket Option executable pricing; fixed 92% payout, spread and latency assumptions are not verified.
- **Report / workflow:** [Sixth-wave discovery run 42810760458](https://github.com/Levon4ik026/HydraAI/actions/runs/42810760458), artifact `hydra-sixth-wave-market-situation-discovery`.
- **Code:** research/sixth_wave_market_situation_screen.py.


## HYD-CAND-011 — Up-shock second-bar reversal, PUT, 15m

- **Status:** Exploratory candidate lead only; not confirmed. Retained because VALIDATION is materially positive (56.52%, n=490, +41.16u), but TRAIN is approximately break-even (50.03%) and TEST falls to 52.04% with -0.48u. It does not meet the 57% target on VALIDATION and has not demonstrated split stability.
- **Signal family:** A completed upward M5 shock candle has true range at least 2× the median true range of the preceding 20 completed M5 candles; the following second bar shows reversal, producing a PUT signal. Signals are based only on closed bars.
- **Execution:** Entry at next M5 open; expiry after 15 minutes (three M5 bars); one active position per family/expiry/continuous segment/split. Original and inverse variants use identical event timestamps and schedule; only CALL/PUT direction changes.
- **Data / accounting:** Dukascopy EUR/USD M1 BID aggregated to M5; 1,061,815 M1 rows; coverage 2024-01-01T22:00Z through 2026-11-08T23:58Z; assumed payout 92% (+0.92u/-1u/0u). This is not Pocket Option executable pricing.
- **Chronological splits:** TRAIN before 2025-09-17; VALIDATION 2025-09-17 through 2026-04-14; TEST from 2026-04-14. Boundary-crossing outcomes purged.
- **Original PUT results:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,573 | 782 / 781 / 10 | 50.03% | [47.56, 52.51]% | -61.56 | 71.60 |
| VALIDATION | 490 | 273 / 210 / 7 | 56.52% | [52.07, 60.87]% | +41.16 | 18.16 |
| TEST | 594 | 306 / 282 / 6 | 52.04% | [48.00, 56.05]% | -0.48 | 32.84 |

- **Exact-schedule inverse CALL audit:**

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,573 | 781 / 782 / 10 | 49.97% | [47.49, 52.44]% | -63.48 | 82.44 |
| VALIDATION | 490 | 210 / 273 / 7 | 43.48% | [39.13, 47.93]% | -79.80 | 81.64 |
| TEST | 594 | 282 / 306 / 6 | 47.96% | [43.95, 52.00]% | -46.56 | 53.36 |

- **Interpretation:** The inverse is materially worse, so retain the original PUT direction as the only exploratory lead. However, its validation advantage does not carry into TEST. This is a useful candidate for later market-context investigation, not evidence of a stable strategy. Do not tune against this TEST.
- **Limitations:** 8 event families × 6 expiries × 2 directions screened; substantial multiple-testing exposure. Wilson intervals do not account for serial dependence. No block bootstrap, matched controls, or platform quote/spread/latency validation. TEST has prior exploratory exposure.
- **Report / workflow:** [Eighth-wave discovery run 42814659845](https://github.com/Levon4ik026/HydraAI/actions/runs/42814659845), artifact `hydra-eighth-wave-market-situation-discovery`.
- **Code:** `research/eighth_wave_market_situation_screen.py`; discovery commit `db311cef57b4ff441361b8b00bd88b58c8fb4704`.


## HYD-CAND-012 — Bearish EMA20/EMA50 cross, inverse CALL, 5m

- **Status:** Exploratory inverse lead; not confirmed. Retained because the exact-schedule inverse has positive assumed-payout net in all three chronological splits and VALIDATION reaches 58.67% (n=229). TRAIN is only 52.28% and TEST is 54.26%, so the evidence is not yet stable and TEST does not meet the 57% discovery target.
- **Original event definition:** On a completed M5 candle, EMA20 crosses from at/above EMA50 to below EMA50, and the signal candle closes below EMA20. The original direction is PUT. The candidate is the exact-event inverse: CALL on those same bearish-cross timestamps. No signal, timestamp, filter, or event schedule is changed.
- **Execution:** Entry at the next M5 open; expiry after the first subsequent M5 bar (5 minutes). One active trade per family/expiry/continuous segment/split. Original and inverse use identical event timestamps and non-overlap schedule.
- **Data / accounting:** Dukascopy EUR/USD M1 BID aggregated to M5; 1,061,815 valid M1 rows; 209,934 M5 bars; coverage 2024-01-01T22:00Z through 2026-11-08T23:58Z. Assumed payout 92% (+0.92u/-1u/0u); break-even decisive WR 52.083%. Not Pocket Option executable pricing.
- **Chronological splits:** TRAIN before 2025-09-17; VALIDATION 2025-09-17 through 2026-04-14; TEST from 2026-04-14. Boundary-crossing outcomes purged.

| Split | Trades | W / L / D | Decisive WR | Wilson 95% CI | Net (u) | Max DD (u) |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 627 | 321 / 293 / 13 | 52.28% | [48.33, 56.20]% | +2.32 | 15.72 |
| VALIDATION | 229 | 132 / 93 / 4 | 58.67% | [52.14, 64.90]% | +28.44 | 7.56 |
| TEST | 193 | 102 / 86 / 5 | 54.26% | [47.12, 61.22]% | +7.84 | 13.32 |

- **Exact-schedule original PUT comparison:** TRAIN 47.72% (293/321/13, n=627, -51.44u); VALIDATION 41.33% (93/132/4, n=229, -46.44u); TEST 45.74% (86/102/5, n=193, -22.88u). Inversion materially improves all three split results on the same event schedule.
- **Interpretation:** A meaningful validation lead with positive assumed-payout net across all splits, but TRAIN is modest and TEST drops below 57%. Wilson intervals are wide and overlap weaker outcomes; they do not account for serial dependence. Keep as a research candidate for later market-context profiling, not a confirmed strategy. Do not tune against this already-exposed TEST.
- **Limitations:** Ninth-wave screen covered 10 directional event families × 6 expiries × 2 variants × 3 splits (360 result rows); multiple-testing exposure and serial dependence remain. No block bootstrap, matched controls, or platform quote/spread/latency validation. Payout is fixed at 92%.
- **Report / workflow:** [Ninth-wave discovery run 42815649623](https://github.com/Levon4ik026/HydraAI/actions/runs/42815649623), artifact `hydra-ninth-wave-market-situation-discovery`.
- **Code:** `research/ninth_wave_market_situation_screen.py`; discovery commit `894fa96da6f41187dcf60209a377b066c142526c`.
