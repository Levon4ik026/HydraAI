# Additional M1 tests: session starts, direction, and weekday-control check

**Status:** exploratory descriptive tests only; no causal claim or trade signal.  
**Branch:** `hydra/research-validation`  
**Source:** `eurusd_history_extended.csv` (blob `ee5f264997f94553818d95ced1d3b11fa58737e1`)  
**Sample:** 30,048 M1 candles, 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC.  
**Event dates:** 2026-10-08, 10-13, 10-15, 10-20, 10-22, 10-23, 10-27 (seven bill/coupon-security issuance settlement dates).

## 1. Session-start replay (first 60 minutes)

Windows:
- UTC day start: 00:00–01:00 UTC.
- London proxy: 07:00–08:00 UTC. This is the London cash-open hour for most of this sample; 27 Oct needs DST awareness, so treat it as a fixed UTC proxy, not a perfect local-open alignment.
- New York proxy: 12:00–13:00 UTC. This is a fixed UTC proxy, not a perfect NYSE/FX-session opening timestamp.

Path = sum of absolute consecutive M1 close changes, pips. Range = max(high)-min(low), pips. Return = last close minus first candle open, pips.

| Window | Event n | Other eligible days n | Event median path | Control median path | Event median range | Control median range | Event up closes | Control up closes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 00:00 UTC | 7 | 14 | 36.4 | 29.7 | 6.9 | 5.2 | 1/7 | 5/14 |
| 07:00 UTC | 7 | 14 | 62.5 | 40.8 | 14.1 | 7.2 | 4/7 | 7/14 |
| 12:00 UTC | 7 | 14 | 63.1 | 46.3 | 20.4 | 9.9 | 7/7 | 7/14 |

**Observation:** the settlement dates had higher median path and range at all three fixed UTC windows. The largest relative range difference appears in the 12:00 UTC window (20.4 vs 9.9 pips). But this is seven dates in a three-week sample, with no macro-news or prior-volatility matching. It is not evidence that the settlement itself caused the move.

## 2. Direction is not stable at the start of the day

On the seven event dates:
- First 60 minutes from 00:00 UTC: 1 positive / 6 negative; median signed return -1.1 pips.
- First 120 minutes: 4 positive / 3 negative; median signed return +6.4 pips.
- 07:00 UTC hour: 4 positive / 3 negative; median signed return +1.2 pips.
- 12:00 UTC hour: 7 positive / 0 negative; median signed return +7.7 pips.

The 12:00 UTC all-positive result is a striking descriptive coincidence, but the non-event controls also had 7 positive out of 14, and the event sample is only seven. The result must not be turned into a CALL rule. Directional behavior is not consistent across the UTC-day opening and London proxy.

## 3. Weekday-control feasibility check

The seven event dates fall on:
- Tuesday: 13, 20, 27 October;
- Thursday: 8, 15, 22 October;
- Friday: 23 October.

Within this short data window, all eligible Tuesday and Thursday dates are event dates. Only two non-event Friday controls have complete first-hour data (9 and 16 October). Therefore a meaningful same-weekday control set cannot be built from this sample.

For transparency, the two Friday controls alone give:
- 00–30 min: event median path 18.7 vs control 20.3 pips; range 4.6 vs 5.9;
- 00–60 min: event median path 36.4 vs control 37.3; range 6.9 vs 6.6;
- 00–120 min: event median path 73.5 vs control 73.6; range 14.4 vs 12.5;
- 00–360 min: event median path 205.7 vs control 247.0; range 23.1 vs 31.9.

These are **not** seven matched pairs: the 2 Friday controls are only a small diagnostic comparison and do not cover Tuesday/Thursday events. Notably, the apparent event-day uplift in the pooled comparison largely disappears in this limited Friday-only comparison.

## 4. What changed versus the earlier report

The prior report's pooled control days were unmatched. This addendum shows why that matters: once we look at the only available weekday overlap, the uplift is not reproduced. The earlier pooled ratios (for example, 1.27x path in the first hour) should be treated as a screening observation, not a stable event effect.

## 5. Decision

**Current conclusion: no validated event-day volatility edge yet.** The initial pattern is interesting enough to justify a longer study, but this M1 sample is structurally inadequate:
1. only seven event dates;
2. only three calendar weeks;
3. no same-weekday controls for Tuesday and Thursday;
4. no controls for CPI, payrolls, Fed/ECB releases, auctions, or prior volatility;
5. current event labels are new-issuance settlement dates, not actual coupon/principal payouts to existing holders.

## 6. Next test gate

Do not optimize entries from this sample. First obtain:
- a real coupon/principal payment calendar from security-level MSPD records;
- several years of EUR/USD M1 with consistent timestamp and quote provenance;
- event dates and amounts separated into principal maturity, coupon, bill redemption, and new-issue settlement;
- matched non-event dates by weekday, session, prior 60-minute volatility, and major-news calendar;
- out-of-sample periods held back before any strategy evaluation.

A result will only be promoted to a HydraAI feature if it survives those controls and a frozen out-of-sample test.
