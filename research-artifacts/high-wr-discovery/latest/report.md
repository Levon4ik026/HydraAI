# HydraAI — fifth-wave high-WR candidate screen

- Captured UTC: 2026-11-15T11:13:37.257587+00:00
- Branch: hydra/research-validation
- Source: Dukascopy EURUSD M1 BID; 1,068,881 valid unique M1 rows; 211,337 complete M5 bars; 2668 continuity segments.
- Coverage: 2024-01-01T22:00:00+00:00 — 2026-11-13T21:59:00+00:00
- M1 gaps: 3644 intervals; 438799 missing minutes; largest 2944 minutes.
- Invalid rows: 0; duplicate rows: 0; conflicting duplicate timestamps: 0; incomplete M5 buckets: 3373.
- Raw CSV SHA-256: 32ab8005153803e0554c4f248b4f77763c1aa5325982bc95087c719a3e849e50; candidate config SHA-256: f80f5dbbc3d3ab2a4ac67f9c10a958c7b571f213f5d881189117443c97582ae3; script SHA-256: 6fb3f858865ae6e9ad893592307678e5a7885581fa20731ea75d4c093eae5415.
- Chronological split by observed UTC dates: TRAIN before 2025-09-21; VALIDATION 2025-09-21–2026-04-18; TEST from 2026-04-19.
- Important: historical TEST is not pristine; the repository has prior broad strategy exploration on overlapping history. Validation is a screening set, not independent proof.
- Signals use completed M5 candles and next M5 open entry. Outcomes settle at the close of the M5 bar corresponding to the fixed expiry. Trades never bridge incomplete M5 buckets or continuity gaps.
- Payout accounting: +0.92u WIN, -1u LOSS, 0u DRAW. Breakeven decisive WR = 52.0833%.
- New prospective cohort starts 2026-11-15 00:00 UTC. Dukascopy data before that time is historical, even if some dates were not in older screens.

## Candidate summary

| ID | Candidate / market situation | Side | Expiry | VALIDATION N | W/L/D | WR | 95% Wilson | Net @92% | PF | Max DD | Max L streak | 5-day block WR CI | Status |
|---|---|---|---:|---:|---|---:|---|---:|---:|---:|---:|---|---|
| HYD-NEW-001 | Tokyo fix post-reversal | fade the EURUSD return over the 60 minutes ending at the fix | 15m | 135 | 65/69/1 | 48.51% | [40.21, 56.89]% | -9.20u | 0.8667 | 22.20u | 8 | [39.55, 56.72]% | SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET |
| HYD-NEW-002 | ECB fix post-reversal | fade the EURUSD return over the 60 minutes ending at the fix | 15m | 147 | 74/72/1 | 50.69% | [42.66, 58.67]% | -3.92u | 0.9456 | 11.40u | 5 | [43.24, 58.67]% | SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET |
| HYD-NEW-003 | London fix post-reversal | fade the EURUSD return over the 60 minutes ending at the fix | 15m | 148 | 74/72/2 | 50.69% | [42.66, 58.67]% | -3.92u | 0.9456 | 17.84u | 7 | [42.67, 59.06]% | SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET |
| HYD-NEW-004 | London opening-hour drift | fixed CALL at the first M5 open at 08:00 London time | 30m | 146 | 65/80/1 | 44.83% | [36.97, 52.95]% | -20.20u | 0.7475 | 30.76u | 13 | [34.90, 55.03]% | SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET |
| HYD-NEW-005 | M5 volatility-squeeze breakout | breakout direction after a 12-bar range falls in the bottom 20% of the preceding 96 rolling 12-bar ranges | 15m | 573 | 278/290/5 | 48.94% | [44.85, 53.05]% | -34.24u | 0.8819 | 41.00u | 9 | [40.54, 57.14]% | SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET |

## Exact candidate cards

### HYD-NEW-001 — Tokyo fix post-reversal

- Family / market state: FX fixing reversal; Fix-window order-flow / benchmark rebalancing; fade the pre-fix EURUSD move.
- Exact entry rule: At each weekday 09:55 local time in Asia/Tokyo, use the 12 complete M5 bars from fix−60m through fix−5m. If the 60m EURUSD move is positive, enter PUT; if negative, enter CALL. Signal is known at the fix; enter at the M5 open exactly at the fix.
- Direction / expiry: direction as above; 15 minutes.
- Raw events / accepted trades: 685 / 685; overlap suppressed 0; split-boundary purged 0.
- VALIDATION: N=135, W/L/D=65/69/1, decisive WR=48.507%, net=-9.20u, expectancy=-0.06815u/trade, PF=0.8667, max DD=22.2u, longest loss streak=8, frequency=0.3209% of M5 bars, WAIT=99.6791%.
- TRAIN: N=408, WR=56.931%, net=+37.60u. TEST (historically exposed): N=142, WR=45.714%, net=-17.12u.
- Same-timestamp baselines on VALIDATION: always CALL WR=59.701%, net=+19.60u; always PUT WR=40.299%, net=-30.32u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.
- VALIDATION payout sensitivity: 50%: -36.50u, 60%: -30.00u, 70%: -23.50u, 80%: -17.00u, 85%: -13.75u, 90%: -10.50u, 92%: -9.20u, 95%: -7.25u, 100%: -4.00u
- VALIDATION monthly stability: 2025-09: n=7 WR=71.429% net=+2.60u; 2025-10: n=22 WR=31.818% net=-8.56u; 2025-11: n=17 WR=35.294% net=-5.48u; 2025-12: n=15 WR=46.667% net=-1.56u; 2026-01: n=19 WR=55.556% net=+1.20u; 2026-02: n=20 WR=35.0% net=-6.56u; 2026-03: n=22 WR=63.636% net=+4.88u; 2026-04: n=13 WR=69.231% net=+4.28u
- New prospective cohort since 2026-11-15: N=0, W/L/D=0/0/0, WR=None%, net=+0.00u.
- Status: **SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET**; batch-eligible (validation N≥30 and ≥10 active UTC days): True.
- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.

### HYD-NEW-002 — ECB fix post-reversal

- Family / market state: FX fixing reversal; Fix-window order-flow / benchmark rebalancing; fade the pre-fix EURUSD move.
- Exact entry rule: At each weekday 14:15 local time in Europe/Berlin, use the 12 complete M5 bars from fix−60m through fix−5m. If the 60m EURUSD move is positive, enter PUT; if negative, enter CALL. Signal is known at the fix; enter at the M5 open exactly at the fix.
- Direction / expiry: direction as above; 15 minutes.
- Raw events / accepted trades: 743 / 743; overlap suppressed 0; split-boundary purged 0.
- VALIDATION: N=147, W/L/D=74/72/1, decisive WR=50.685%, net=-3.92u, expectancy=-0.02667u/trade, PF=0.9456, max DD=11.4u, longest loss streak=5, frequency=0.3494% of M5 bars, WAIT=99.6506%.
- TRAIN: N=446, WR=52.822%, net=+6.28u. TEST (historically exposed): N=150, WR=48.98%, net=-8.76u.
- Same-timestamp baselines on VALIDATION: always CALL WR=45.89%, net=-17.36u; always PUT WR=54.11%, net=+5.68u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.
- VALIDATION payout sensitivity: 50%: -35.00u, 60%: -27.60u, 70%: -20.20u, 80%: -12.80u, 85%: -9.10u, 90%: -5.40u, 92%: -3.92u, 95%: -1.70u, 100%: +2.00u
- VALIDATION monthly stability: 2025-09: n=7 WR=71.429% net=+2.60u; 2025-10: n=23 WR=60.87% net=+3.88u; 2025-11: n=20 WR=25.0% net=-10.40u; 2025-12: n=22 WR=72.727% net=+8.72u; 2026-01: n=21 WR=45.0% net=-2.72u; 2026-02: n=20 WR=50.0% net=-0.80u; 2026-03: n=22 WR=50.0% net=-0.88u; 2026-04: n=12 WR=33.333% net=-4.32u
- New prospective cohort since 2026-11-15: N=0, W/L/D=0/0/0, WR=None%, net=+0.00u.
- Status: **SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET**; batch-eligible (validation N≥30 and ≥10 active UTC days): True.
- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.

### HYD-NEW-003 — London fix post-reversal

- Family / market state: FX fixing reversal; Fix-window order-flow / benchmark rebalancing; fade the pre-fix EURUSD move.
- Exact entry rule: At each weekday 16:00 local time in Europe/London, use the 12 complete M5 bars from fix−60m through fix−5m. If the 60m EURUSD move is positive, enter PUT; if negative, enter CALL. Signal is known at the fix; enter at the M5 open exactly at the fix.
- Direction / expiry: direction as above; 15 minutes.
- Raw events / accepted trades: 743 / 742; overlap suppressed 0; split-boundary purged 0.
- VALIDATION: N=148, W/L/D=74/72/2, decisive WR=50.685%, net=-3.92u, expectancy=-0.02649u/trade, PF=0.9456, max DD=17.84u, longest loss streak=7, frequency=0.3518% of M5 bars, WAIT=99.6482%.
- TRAIN: N=444, WR=55.455%, net=+28.48u. TEST (historically exposed): N=150, WR=46.667%, net=-15.60u.
- Same-timestamp baselines on VALIDATION: always CALL WR=45.205%, net=-19.28u; always PUT WR=54.795%, net=+7.60u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.
- VALIDATION payout sensitivity: 50%: -35.00u, 60%: -27.60u, 70%: -20.20u, 80%: -12.80u, 85%: -9.10u, 90%: -5.40u, 92%: -3.92u, 95%: -1.70u, 100%: +2.00u
- VALIDATION monthly stability: 2025-09: n=7 WR=42.857% net=-1.24u; 2025-10: n=23 WR=61.905% net=+3.96u; 2025-11: n=20 WR=55.0% net=+1.12u; 2025-12: n=22 WR=40.909% net=-4.72u; 2026-01: n=21 WR=47.619% net=-1.80u; 2026-02: n=20 WR=35.0% net=-6.56u; 2026-03: n=22 WR=59.091% net=+2.96u; 2026-04: n=13 WR=61.538% net=+2.36u
- New prospective cohort since 2026-11-15: N=0, W/L/D=0/0/0, WR=None%, net=+0.00u.
- Status: **SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET**; batch-eligible (validation N≥30 and ≥10 active UTC days): True.
- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.

### HYD-NEW-004 — London opening-hour drift

- Family / market state: Local-session seasonality; London local-session opening-hour seasonal drift.
- Exact entry rule: At the first eligible M5 open at 08:00 Europe/London on weekdays, enter CALL. The preceding 07:55–08:00 M5 bar is the completed timing bar; no price filter.
- Direction / expiry: direction as above; 30 minutes.
- Raw events / accepted trades: 744 / 743; overlap suppressed 0; split-boundary purged 0.
- VALIDATION: N=146, W/L/D=65/80/1, decisive WR=44.828%, net=-20.20u, expectancy=-0.13836u/trade, PF=0.7475, max DD=30.76u, longest loss streak=13, frequency=0.3471% of M5 bars, WAIT=99.6529%.
- TRAIN: N=447, WR=53.273%, net=+10.12u. TEST (historically exposed): N=150, WR=54.362%, net=+6.52u.
- Same-timestamp baselines on VALIDATION: always CALL WR=44.828%, net=-20.20u; always PUT WR=55.172%, net=+8.60u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.
- VALIDATION payout sensitivity: 50%: -47.50u, 60%: -41.00u, 70%: -34.50u, 80%: -28.00u, 85%: -24.75u, 90%: -21.50u, 92%: -20.20u, 95%: -18.25u, 100%: -15.00u
- VALIDATION monthly stability: 2025-09: n=7 WR=57.143% net=+0.68u; 2025-10: n=23 WR=39.13% net=-5.72u; 2025-11: n=20 WR=65.0% net=+4.96u; 2025-12: n=21 WR=61.905% net=+3.96u; 2026-01: n=21 WR=28.571% net=-9.48u; 2026-02: n=20 WR=42.105% net=-3.64u; 2026-03: n=22 WR=27.273% net=-10.48u; 2026-04: n=12 WR=50.0% net=-0.48u
- New prospective cohort since 2026-11-15: N=0, W/L/D=0/0/0, WR=None%, net=+0.00u.
- Status: **SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET**; batch-eligible (validation N≥30 and ≥10 active UTC days): True.
- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.

### HYD-NEW-005 — M5 volatility-squeeze breakout

- Family / market state: Volatility compression/expansion; Low-volatility compression followed by directional range expansion.
- Exact entry rule: On a completed M5 bar, require the immediately preceding 12-bar high-low range to be no greater than the 20th percentile of the 96 earlier rolling 12-bar ranges (all reference windows end before the current signal bar). Enter CALL on a bullish close above the prior 12-bar high; enter PUT on a bearish close below the prior 12-bar low. Entry next M5 open.
- Direction / expiry: direction as above; 15 minutes.
- Raw events / accepted trades: 4156 / 2978; overlap suppressed 1178; split-boundary purged 0.
- VALIDATION: N=573, W/L/D=278/290/5, decisive WR=48.944%, net=-34.24u, expectancy=-0.05976u/trade, PF=0.8819, max DD=41.0u, longest loss streak=9, frequency=1.3621% of M5 bars, WAIT=98.6379%.
- TRAIN: N=1831, WR=47.215%, net=-169.48u. TEST (historically exposed): N=574, WR=47.059%, net=-54.12u.
- Same-timestamp baselines on VALIDATION: always CALL WR=49.296%, net=-30.40u; always PUT WR=50.704%, net=-15.04u; theoretical random-direction reference=50% decisive WR / −0.04u per trade at 92%.
- VALIDATION payout sensitivity: 50%: -151.00u, 60%: -123.20u, 70%: -95.40u, 80%: -67.60u, 85%: -53.70u, 90%: -39.80u, 92%: -34.24u, 95%: -25.90u, 100%: -12.00u
- VALIDATION monthly stability: 2025-09: n=24 WR=54.167% net=+0.96u; 2025-10: n=104 WR=48.039% net=-7.92u; 2025-11: n=78 WR=49.351% net=-4.04u; 2025-12: n=77 WR=52.0% net=-0.12u; 2026-01: n=73 WR=50.685% net=-1.96u; 2026-02: n=85 WR=48.235% net=-6.28u; 2026-03: n=95 WR=51.579% net=-0.92u; 2026-04: n=37 WR=32.432% net=-13.96u
- New prospective cohort since 2026-11-15: N=0, W/L/D=0/0/0, WR=None%, net=+0.00u.
- Status: **SCREENED_NO_EDGE_AT_92_OR_WR_TARGET_NOT_MET**; batch-eligible (validation N≥30 and ≥10 active UTC days): True.
- Limitations: Dukascopy BID is not Pocket Option executable pricing; no spread, latency, platform payout or settlement model. Fixing candidates share one literature mechanism and are correlated hypotheses, not three independent replications.

## Interpretation

- Batch eligibility: 5/5 candidates meet the predeclared minimum of at least 30 VALIDATION trades and 10 active UTC days. Batch-ready=True.
- A candidate is only preliminarily promising if VALIDATION WR≥57%, net @92% >0 and PF>1; this is a screening label, not confirmation.
- Wilson intervals assume independent decisive outcomes; 5-day moving-block bootstrap is descriptive and does not remove all serial dependence or multiple-testing bias.
- Historical TEST was previously exposed to broad repository research. The only new prospective cohort begins 2026-11-15; early forward N is expected to be small.
- No rules were tuned on TEST. No production, stabilization, real trading, OTC or auto-trading code was changed.

## Literature used only to motivate hypotheses

- Krohn, Mueller & Whelan, “Foreign Exchange Fixings and Returns around the Clock”, Journal of Finance 79(1), first published 18 Dec 2023: https://doi.org/10.1111/jofi.13306
- Breedon & Ranaldo, “Intraday Patterns in FX Returns and Order Flow”, Swiss National Bank Working Paper 2011-04, 23 Mar 2011: https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04
- Ito & Hashimoto, “Intra-Day Seasonality in Activities of the Foreign Exchange Markets”, NBER Working Paper 12413, Aug 2006: https://www.nber.org/papers/w12413

## Reproducibility

- Machine-readable manifest: manifest.json; trade ledger: trades.csv (workflow artifact).
- Source dataset SHA-256 and exact candidate configuration hash are recorded in the manifest.
