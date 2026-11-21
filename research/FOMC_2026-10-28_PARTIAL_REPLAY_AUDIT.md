# FOMC Decision Replay: 28 October 2026 — Partial Observation Audit

**Branch:** `hydra/research-validation`  
**Input:** `observer_data/market_observations.csv`, blob `b8d5767e1af5b96197038d966a79bbdc71b5db52`  
**Event:** FOMC rate decision, 2026-10-28 18:00 UTC (14:00 US Eastern)  
**Status:** partial replay only; not a complete M1 event study.

## Why this file matters

The extended historical OHLC file ends at 01:19 UTC on Oct 28 and therefore does not include the FOMC decision. However, the repository also contains a separate observer log with candle timestamps and close/range observations from Oct 28 evening and Oct 29. This makes it possible to inspect part of the FOMC reaction, but not to treat it as a complete minute-by-minute series.

## Coverage audit: 18:00–19:00 UTC

The one-hour interval contains 60 possible minute timestamps. The observer log has 29 unique minute records:

- First observed candle: 18:00 UTC.
- Last observed candle: 18:59 UTC.
- Coverage: 29/60 minutes (48.3%).
- Missing minutes: 31.
- Two gaps: 18:19 to 18:41 (21 missing minutes), and 18:45 to 18:56 (10 missing minutes).

The data is not continuous and has no bid/ask fields.

## What can be measured without hiding the gaps

| Measure | Result |
|---|---:|
| Observed minute records | 29 |
| Sum of absolute close changes across all adjacent records | 85.0 pips |
| Of which changes between truly consecutive 1-minute records | 51.9 pips |
| Of which jumps spanning missing intervals | 33.1 pips |
| Close-to-close change from first to last observed candle | +14.8 pips |
| Largest single recorded candle high-low range | 11.5 pips |

**Critical:** 85.0 pips is not a valid one-hour M1 path measure because 33.1 pips of it comes from jumps across missing intervals. It must not be compared directly with continuous M1 event windows. The +14.8 pip endpoint change is also only from the first to last observed close; it does not reveal the path between them.

The log first records a candle at 18:00, but its observation timestamp is 18:00:38. Some later records are observed in batches, which is consistent with the missing minute coverage and means the event-time stream was not captured reliably enough for a short-expiry execution study.

## Decision

This partial observer log does **not** validate an FOMC trading signal. It does establish that the repository contains post-decision observations that were not present in the extended historical OHLC file, while also documenting why they cannot support a precise 1/5/15-minute backtest.

For a valid FOMC study we need continuous, timestamp-verified M1 candles (preferably BID and ASK) from at least 30 minutes before through 2 hours after the statement and press conference. The collector must confirm every minute, preserve missing-minute markers, and not interpolate gaps.

## Research conclusion

- Do not infer a CALL/PUT direction from this one partial event.
- Do not use the 85.0-pip sampled path as if it were continuous.
- Treat this as a data-capture quality finding and a useful target for the next prospective event-capture test.
