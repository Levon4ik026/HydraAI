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
- **Preliminary inverse results:** These figures are derived exactly by swapping W and L in the original report's identical event cohort; draws remain unchanged. A corrected rerun is in progress to independently produce full inverse outcome sequences and drawdown metrics.

| Split | Trades | Inverse W / L / D | Decisive WR | Net (u) |
|---|---:|---:|---:|---:|
| TRAIN | 1,887 | 967 / 910 / 10 | 51.52% | -20.36 |
| VALIDATION | 606 | 345 / 253 / 8 | 57.69% | +64.40 |
| TEST | 547 | 289 / 254 / 4 | 53.22% | +11.88 |

- **Interpretation:** Validation clears the 57% discovery threshold with a substantial sample, and TEST is above the 52.08% assumed-payout break-even rate with positive net. TRAIN is below break-even and the TEST result is materially weaker than VALIDATION. This is therefore a lead worth retaining, not evidence of stable performance.
- **Uncertainty:** Original report's Wilson interval for the inverse validation cohort can be recomputed after corrected rerun; no block-bootstrap or matched-control test yet. Multiple-testing bias remains.
- **Important:** Do not infer max drawdown from aggregate W/L/D counts. Await corrected report with the ordered inverse outcomes before recording drawdown or ranking this as a strong candidate.
- **Code / report:** research/second_wave_strategy_screen.py; corrected inverse calculation workflow run 42724247482 is pending.
