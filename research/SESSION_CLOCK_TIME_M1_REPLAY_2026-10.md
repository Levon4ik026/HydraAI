# EUR/USD M1 — Session-Start and Intraday Clock Replay (2026-10)

**Repository branch:** `hydra/research-validation`  
**Input:** `eurusd_history_extended.csv` (blob `ee5f264997f94553818d95ced1d3b11fa58737e1`)  
**Coverage:** 2026-10-07 through 2026-10-28; 30,048 M1 rows; 16 weekdays with complete sample days.  
**Status:** descriptive pilot only.

## Question

Does EUR/USD show a repeatable volatility or directional pattern at common session clock times, independent of a specific macro release?

## Method

For each UTC clock time, measure the first 15, 30 and 60 minutes. Path is the sum of absolute consecutive M1 close changes (pips); range is max high minus min low (pips); signed return is last close minus first open. For the headline comparison, only weekdays are included. The sample is too short for reliable inference and no spread/quote-side correction or matched controls are available.

## Main results — all available days

| UTC start | Window | Complete days | Median path (pips) | Median range (pips) | Up / down signed closes |
|---|---:|---:|---:|---:|---:|
| 07:00 | 15 min | 21 | 12.4 | 5.6 | 5 / 13 |
| 07:00 | 30 min | 21 | 23.5 | 10.1 | 8 / 10 |
| 07:00 | 60 min | 21 | 55.9 | 10.4 | 11 / 10 |
| 12:30 | 15 min | 21 | 13.4 | 5.9 | 9 / 11 |
| 12:30 | 30 min | 21 | 28.2 | 9.1 | 13 / 7 |
| 12:30 | 60 min | 21 | 56.3 | 10.7 | 10 / 10 |
| 13:30 | 15 min | 21 | 14.4 | 7.2 | 11 / 8 |
| 13:30 | 30 min | 21 | 29.1 | 9.3 | 12 / 9 |
| 13:30 | 60 min | 21 | 64.2 | 12.8 | 11 / 9 |
| 14:00 | 15 min | 21 | 16.5 | 8.0 | 13 / 7 |
| 14:00 | 30 min | 21 | 32.4 | 10.3 | 14 / 7 |
| 14:00 | 60 min | 21 | 61.6 | 10.9 | 15 / 5 |
| 19:30 | 15 min | 21 | 7.9 | 3.3 | 8 / 12 |
| 19:30 | 30 min | 21 | 15.9 | 4.3 | 6 / 12 |
| 19:30 | 60 min | 21 | 29.2 | 7.8 | 10 / 11 |
| 20:30 | 15 min | 21 | 6.3 | 2.5 | 10 / 10 |
| 20:30 | 30 min | 21 | 14.1 | 3.8 | 13 / 8 |
| 20:30 | 60 min | 21 | 37.4 | 6.2 | 13 / 7 |

Weekend observations are included in this broad table, so use the weekday-only summary below for session interpretation.

## Weekday-only comparison (16 days)

| UTC start | Window | Days | Median path | Median range | Median signed return | Up / down |
|---|---:|---:|---:|---:|---:|---:|
| 07:00 | 30 min | 15 | 34.4 | 10.7 | -0.3 | 6 / 8 |
| 13:30 | 30 min | 15 | 34.3 | 10.8 | -1.2 | 7 / 8 |
| 14:00 | 30 min | 15 | 34.9 | 10.3 | +1.9 | 10 / 5 |

The 07:00 UTC and 13:30 UTC windows have almost identical median path and range in this sample. The 14:00 UTC window has more positive closes (10 of 15), but the median signed return is only +1.9 pips and the sample has 15 days. This is not a robust directional result.

## Interpretation

1. There is a visible intraday clock-time profile: 19:30 and 20:30 UTC are quieter in this sample than 07:00–14:00 UTC.
2. The data does not show a strong direction at 07:00 or 13:30 UTC. Their 30-minute median signed returns are slightly negative and close to zero.
3. The apparent 14:00 UTC positive skew is exploratory only and could be driven by a few sessions, coincident releases, or data quality.
4. The dataset includes weekend timestamps. Weekend rows should be excluded from any FX session analysis and checked against a second source.
5. The earlier Oct 14 CPI outlier remains quarantined pending independent verification. It must not be allowed to dominate event or session conclusions.

## Research decision

No session-open CALL/PUT bias is supported by this replay. The only defensible lead is to investigate volatility by time-of-day on a multi-year, weekday-only BID/ASK dataset, controlling for macro releases, weekday, pre-window volatility and market regime. Do not turn these descriptive medians into a trading rule.
