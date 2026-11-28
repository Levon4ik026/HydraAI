# Additional Event Replay: PMI, Fed Publications and Industrial Production (October 2026)

**Branch:** `hydra/research-validation`  
**Input:** `eurusd_history_extended.csv`, blob `ee5f264997f94553818d95ced1d3b11fa58737e1`  
**Coverage:** 2026-10-07 04:31 UTC to 2026-10-28 01:19 UTC  
**Rows:** 30,048 M1 candles  
**Status:** small-sample exploratory replay; not a strategy validation.

## 1. Events added in this replay

Official / primary calendar references:
- Federal Reserve October 2026 calendar: FOMC minutes on Oct 7 at 2:00 p.m. ET; Beige Book Oct 14 at 2:00 p.m. ET; industrial production (G.17) Oct 16 at 9:15 a.m. ET; October FOMC decision on Oct 28 at 2:00 p.m. ET. https://www.federalreserve.gov/newsevents/2026-october.htm
- Federal Reserve October FOMC statement release: Oct 28 at 2:00 p.m. ET. https://www.federalreserve.gov/monetarypolicy/fomcpresconf20261028.htm
- Eurostat October release calendar lists euro-area HICP on Oct 16, industrial production on Oct 15, GDP update Oct 20, government debt/deficit Oct 21, and Q3 flash GDP Oct 30. https://ec.europa.eu/eurostat/web/main/news/euro-indicators/release-calendar
- S&P Global flash PMI release schedule and event time confirmation: Eurozone flash PMI Oct 23 08:00 UTC; US flash PMI Oct 23 13:45 UTC. The exact October release times are corroborated by the Oct 23 event preview. https://primexbt.com/market-research/flash-pmis-preview-the-last-read-on-the-economy-before-the-fed-decides/

## 2. Method

For each event, measured complete 5, 15, 30 and 60 minute windows immediately before and after the scheduled timestamp:
- Path = sum of absolute consecutive M1 close-to-close changes, in pips.
- Range = max high minus min low, in pips.
- Signed return = final close minus first candle open, in pips.

For Wednesday/Friday events, a minimal same-weekday control was formed from the other two available Wednesdays/Fridays at the same UTC clock time. This is not a proper matched sample: only two controls per event, and they may contain their own news.

Eastern Time in October 2026 was converted using UTC−4.

## 3. S&P Global flash PMI — Friday Oct 23

### Eurozone flash PMI — 08:00 UTC

| Window | Pre path | Post path | Post range | Post signed return | Same-Friday control post path (n=2) |
|---|---:|---:|---:|---:|---:|
| 5 min | 4.8 | 3.0 | 1.8 | +1.6 | 4.1 |
| 15 min | 11.1 | 11.6 | 6.0 | +4.0 | 12.9 |
| 30 min | 24.0 | 21.6 | 6.0 | +0.6 | 27.7 |
| 60 min | 62.5 | 60.2 | 17.8 | -7.4 | 55.5 |

The event window does not show a clear volatility burst relative to the two Friday controls. Direction changes with the horizon: modest positive first 15 minutes, almost flat at 30 minutes, negative by 60 minutes.

### US flash PMI — 13:45 UTC

| Window | Pre path | Post path | Post range | Post signed return | Same-Friday control post path (n=2) |
|---|---:|---:|---:|---:|---:|
| 5 min | 6.6 | 6.8 | 5.7 | -0.3 | 4.5 |
| 15 min | 17.1 | 18.5 | 7.7 | +1.4 | 12.8 |
| 30 min | 30.2 | 34.5 | 12.3 | +5.4 | 33.3 |
| 60 min | 72.5 | 65.8 | 12.3 | +2.7 | 63.1 |

The first 15 minutes are somewhat more active than the two Friday controls, but the 30- and 60-minute path differences are small. No stable directional conclusion is supported. The 5-minute window is particularly noisy.

## 4. Federal Reserve and US industrial production

### FOMC minutes — Oct 7, 18:00 UTC

| Window | Event post path | Event post range | Event signed return | Same-Wednesday control post path (n=2) |
|---|---:|---:|---:|---:|
| 15 min | 17.1 | 7.3 | +0.2 | 9.1 |
| 30 min | 25.7 | 7.3 | +0.4 | 18.4 |
| 60 min | 42.8 | 7.3 | +0.3 | 47.8 |

There is a modest path uplift at 15/30 minutes, but almost no net directional move. At 60 minutes event path is below the control median. Two controls are inadequate.

### Beige Book — Oct 14, 18:00 UTC

| Window | Event post path | Event post range | Event signed return | Same-Wednesday control post path (n=2) |
|---|---:|---:|---:|---:|
| 15 min | 10.9 | 8.5 | +8.3 | 12.2 |
| 30 min | 21.1 | 13.3 | +13.1 | 20.7 |
| 60 min | 57.3 | 19.5 | +16.3 | 40.6 |

The 60-minute window is more active than the two controls, but most of the move is not an immediate 15-minute impulse. The observed upward close is one date only and cannot establish a directional Beige Book effect.

### Industrial production (G.17) — Oct 16, 13:15 UTC

| Window | Event post path | Event post range | Event signed return | Same-Friday control post path (n=2) |
|---|---:|---:|---:|---:|
| 15 min | 11.7 | 4.0 | -1.8 | 12.3 |
| 30 min | 21.0 | 10.7 | +6.9 | 30.7 |
| 60 min | 59.1 | 23.3 | +10.2 | 63.9 |

No immediate volatility increase is evident versus the tiny Friday control group. The sign flips from negative at 15 minutes to positive later.

## 5. Important event not testable in the current file

The October FOMC rate decision and press conference occurred on Oct 28 at 2:00 p.m. ET (18:00 UTC). The EUR/USD file ends at 01:19 UTC on Oct 28, so it contains none of the decision window. It would be incorrect to report a reaction test for this event from the current file.

Eurostat's HICP publication date is listed as Oct 16, but the calendar page consulted did not provide a precise publication timestamp in the retrieved record. It is therefore not included in minute-level event-window calculations rather than guessing the time.

## 6. Conclusions

1. Neither Eurozone nor US flash PMI shows a convincing, repeatable impulse in this one-event sample.
2. FOMC minutes show some short-window activity but almost no net movement; Beige Book has a later one-hour move, not a robust immediate reaction.
3. US industrial production does not outperform the small same-weekday control group on path activity.
4. The FOMC decision itself is absent from the available candles and needs an extended data file.
5. The control groups are only two days each. These are descriptive checks, not statistically meaningful matched controls.

## 7. Research decision

No CALL/PUT rule is approved. The next useful step is not adding more one-off events to this three-week sample; it is obtaining several years of clean EUR/USD M1 BID/ASK data and a timestamped historical event calendar. Then event families can be compared with weekday/session/pre-volatility matched controls and tested on untouched out-of-sample periods.
