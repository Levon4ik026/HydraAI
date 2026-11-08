# Repository Data Inventory and Observer Latency Audit — 9 November 2026

**Branch:** `hydra/research-validation`

## Executive result

A repository-wide check of the available EUR/USD data found one important correction to the earlier FOMC replay:

**`observer_data/market_observations.csv` is not a real-time minute feed. Its recorded observation timestamps lag the candle timestamps substantially.** Across 374 rows, the observed latency is:

| Metric | Delay |
|---|---:|
| Minimum | 81 seconds |
| Median | 220 seconds (3 min 40 sec) |
| 90th percentile | 338 seconds (5 min 38 sec) |
| Maximum | 1,594 seconds (26 min 34 sec) |

Therefore this observer log cannot validate 1-minute or 5-minute reaction timing around news. A row may be written several minutes after the candle it describes.

## 1. Historical OHLC files: duplicate coverage, not extra history

Compared:
- `eurusd_history_10000.csv`: 10,049 rows, 2026-10-21 01:51 UTC through 2026-10-28 01:19 UTC.
- `eurusd_history_extended.csv`: 30,048 rows, 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC.

All 10,049 timestamps in the shorter file are present in the extended file, and all four OHLC values match exactly on every overlapping row (0 mismatches).

**Conclusion:** the 10k file is a subset/duplicate of the extended history, not an independent data source and not a way to extend the timeline beyond Oct 28 01:19 UTC.

The extended file contains 30,048 rows and one missing minute across its full interval. The shorter file contains 2,880 Saturday/Sunday rows; weekend observations must be excluded from FX weekday/session comparisons.

## 2. Observer log coverage

`observer_data/market_observations.csv` contains 374 rows across Oct 28–29, 2026. It is fragmented into multiple runs rather than a continuous minute series.

Longest continuous runs:
- Oct 29 18:48–20:06 UTC: 79 candles.
- Oct 29 15:24–16:32 UTC: 69 candles.
- Oct 29 17:53–18:21 UTC: 29 candles.
- Oct 28 17:55–18:19 UTC: 25 candles.
- Oct 28 20:45–21:09 UTC: 25 candles.
- Oct 29 16:34–16:58 UTC: 25 candles.

This means the FOMC statement window on Oct 28 (18:00 UTC) has only a 25-minute continuous segment from 17:55 to 18:19, then a 21-minute gap before the next observed candle at 18:41. The press conference begins around 18:30 UTC, so its immediate reaction is not captured continuously.

## 3. Correction to interpretation of the earlier FOMC report

The earlier partial replay correctly warned that the 18:00–19:00 interval had 29 observed candle timestamps and 31 missing minutes. This audit adds a further limitation: **those candle observations were delayed**. The first log row was written at 18:00:38 but described the 17:55 candle. It was not a live 18:00 candle observation.

The measured +14.8 pip difference between first and last observed closes remains a description of those sampled endpoints only. It must not be presented as a clean one-hour FOMC response. The 85.0-pip sampled path is invalid as continuous M1 path activity; 33.1 pips came from jumps over missing minutes.

## 4. Research decision

1. Do not use the 10k file as an independent confirmation of the extended dataset.
2. Do not use `market_observations.csv` for 1m/5m news-event signal testing.
3. For event research, use continuous OHLC candles with verified candle timestamps; ideally obtain BID/ASK or tick data to model spread and executable prices.
4. Keep observer logs for diagnostics and data-pipeline monitoring, not as a substitute for a historical market feed.
5. Before the next scheduled macro-event capture, require the collector to demonstrate near-real-time timestamps, continuous minute coverage, and explicit gap alarms.

## Bottom line

The main historical OHLC dataset is internally consistent enough for exploratory descriptive tests, but covers only about three weeks. The supposed additional post-Oct-28 observer history is delayed and fragmented. No new CALL/PUT edge can be claimed from it.
