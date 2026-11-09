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
