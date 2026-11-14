# BLS / FOMC release-day EUR/USD M1 matched-control study

**Date:** 2026-11-09  
**Branch:** `hydra/research-validation`  
**Dataset:** `eurusd_research_clean.csv`, 486,488 rows, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.  
**Purpose:** Test whether scheduled US CPI, Employment Situation (NFP), PPI, FOMC statement and FOMC minutes release times show repeatable intraday activity or directional behavior versus comparable ordinary weekdays.

## Executive result

This first full-history matched-control test does **not** establish a tradable event-day edge. It finds some differences worth testing again, but the signs are inconsistent and the samples remain small:

- CPI: the 30-minute post-release window had lower median path activity than matched controls (17.25 vs 20.45 pips) and was positive on only 5 of 14 dates.
- NFP: the 30-minute signed return was negative on 8 of 13 dates; at 60 minutes only 3 of 13 were positive. This is a possible downside-skew hypothesis, not a validated PUT signal.
- PPI: 9 of 14 dates were positive over 30 minutes and 9 of 14 over 60 minutes. Median 30-minute signed return was +1.55 pips, versus -1.35 pips for controls. Removing the largest absolute event return still leaves 8/13 positive, but the sample is too small and the result is not an out-of-sample strategy test.
- FOMC statements: no stable direction. The 30-minute positive share was 5/11 (45.5%), essentially no advantage over matched controls (51.5%).
- FOMC minutes: 6/10 positive over 30 minutes, but the median signed move falls from +2.10 pips to +0.40 pips when the largest absolute move is removed. No robust direction is established.

The most important observation is that **release days did not consistently create more movement than matched ordinary days**. CPI and FOMC statement days were quieter by median 30-minute path; NFP and PPI were only modestly higher; minutes showed a modest uplift. The results do not justify turning the event calendar into an automatic CALL/PUT rule.

## Data and integrity

The source file contains 486,488 one-minute EUR/USD OHLC rows. The prior integrity audit found no duplicate timestamps, no non-increasing timestamp steps, and no invalid OHLC bars. It does contain sparse missing intervals in the overall history. For this event study, a window was accepted only if every required one-minute candle was present.

All 14 CPI, 13 NFP, 14 PPI, 11 FOMC statement and 10 FOMC minutes events had complete pre-event 30-minute and post-event 5/15/30/60-minute windows. That is 62 event observations. March 18, 2026 appears in both the PPI and FOMC statement categories, because both releases occurred on that date at different times; these are not independent calendar days.

## Event ledger and time conversion

Release times were treated as New York local time and converted to UTC with the IANA `America/New_York` timezone, including daylight-saving transitions. BLS CPI, NFP and PPI releases were tested at 08:30 ET. FOMC statement and minutes releases were tested at 14:00 ET.

- CPI dates tested: 2025-08-12, 2025-09-11, 2025-10-24, 2025-12-18; 2026-01-13, 02-13, 03-11, 04-10, 05-12, 06-10, 07-14, 08-12, 09-11, 10-14.
- NFP dates tested: 2025-09-05, 2025-11-20, 2025-12-16; 2026-01-09, 02-11, 03-06, 04-03, 05-08, 06-05, 07-02, 08-07, 09-04, 10-02.
- PPI dates tested: 2025-08-14, 2025-09-10, 2025-11-25; 2026-01-14, 01-30, 02-27, 03-18, 04-14, 05-13, 06-11, 07-15, 08-13, 09-10, 10-15. The October 2025 PPI report was not published during the 2025 lapse in appropriations; the September 2025 report moved to November 25, and November 2025 PPI moved to January 14, 2026.
- FOMC statement dates tested: 2025-07-30, 09-17, 10-29, 12-10; 2026-01-28, 03-18, 04-29, 06-17, 07-29, 09-16, 10-28.
- FOMC minutes dates tested: 2025-08-20, 10-08, 11-19; 2026-01-07, 02-18, 04-08, 05-20, 07-08, 08-19, 10-07.

Official calendar validation:
- BLS 2025 and 2026 CPI schedules and release changes: https://www.bls.gov/schedule/news_release/cpi.htm and https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
- BLS Employment Situation schedule and revised dates: https://www.bls.gov/schedule/news_release/empsit.htm and https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
- BLS PPI 2025/2026 schedules and shutdown adjustments: https://www.bls.gov/ppi/detailed-report/ppi-detailed-report-september-2025.pdf, https://www.bls.gov/web/ppi/ppi_dr.pdf, https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm
- FOMC meeting and minutes calendar: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Matched-control method

For every event, three control dates were selected from the same weekday within +/-35 calendar days, at the same New York local release clock time. All dates in the compiled CPI/NFP/PPI/FOMC event ledger were excluded from the control pool. Controls were ranked by similarity of the preceding 30-minute absolute close-to-close path (nearest absolute log-ratio), and the three closest valid controls were retained.

For each event and control:
- pre-event volatility match: 30-minute path immediately before the scheduled release;
- post-event horizons: 5, 15, 30 and 60 minutes, starting with the one-minute candle stamped at the release minute;
- path: sum of absolute one-minute close-to-close changes;
- range: maximum high minus minimum low across the window;
- signed move: final close minus the first candle's open;
- direction: positive if signed move > 0, otherwise non-positive.

All price distances are pips (0.0001). These are candle-based price movements, not executable Pocket Option returns: spread, payout changes, quote-side differences, entry latency and expiry settlement rules are not represented.

## Results: median activity and 30-minute direction

| Event group | n | 30m median path: event | 30m median path: controls | 30m median signed: event | 30m median signed: controls | Positive event days | Positive controls |
|---|---:|---:|---:|---:|---:|---:|---:|
| CPI | 14 | 17.25 | 20.45 | -1.90 | +0.90 | 5/14 (35.7%) | 52.4% |
| NFP | 13 | 19.10 | 17.50 | -1.70 | +1.50 | 5/13 (38.5%) | 59.0% |
| PPI | 14 | 20.50 | 19.75 | +1.55 | -1.35 | 9/14 (64.3%) | 45.2% |
| FOMC statement | 11 | 23.40 | 26.40 | -1.30 | -0.10 | 5/11 (45.5%) | 51.5% |
| FOMC minutes | 10 | 24.00 | 21.40 | +2.10 | -1.10 | 6/10 (60.0%) | 53.3% |

The 30-minute event/control medians are computed across event observations after taking the median of each event's three matched controls. The positive-control share is the mean of the per-event control positive shares.

## Horizon-by-horizon median path (pips)

| Event group | 5m event / control | 15m event / control | 30m event / control | 60m event / control |
|---|---:|---:|---:|---:|
| CPI | 2.05 / 2.45 | 8.65 / 10.75 | 17.25 / 20.45 | 38.05 / 43.25 |
| NFP | 2.80 / 2.80 | 8.90 / 9.50 | 19.10 / 17.50 | 38.50 / 42.80 |
| PPI | 2.95 / 2.70 | 10.45 / 9.70 | 20.50 / 19.75 | 41.00 / 41.60 |
| FOMC statement | 2.20 / 3.90 | 11.00 / 11.80 | 23.40 / 26.40 | 44.90 / 47.70 |
| FOMC minutes | 3.75 / 3.15 | 13.15 / 11.25 | 24.00 / 21.40 | 46.40 / 44.00 |

## Directional findings and caveats

### CPI
The 30-minute post-release signed return was positive on 5/14 days. At 30 and 60 minutes the event-day median path was below the matched-control median. This does not support a generic “CPI means volatility spike” assumption in this sample.

### NFP
At 30 minutes, 5/13 events were positive; at 60 minutes, only 3/13 were positive (23.1%), versus 59.0% positive matched controls at 30 minutes and 59.0% at 60 minutes? The 60-minute control positive share was 59.0% as well. This is the clearest downside-skew candidate in this pass, but the events are heterogeneous and n=13 is far too small to promote it to a trading rule. The event sample also includes a revised release date after the 2025 shutdown.

### PPI
PPI had the strongest positive direction count: 9/14 positive over 30 minutes and 9/14 over 60 minutes. However, the 30-minute median signed return was only +1.55 pips. The largest positive outlier was January 30, 2026 (+14.7 pips over 30 minutes). Removing the largest absolute event move leaves 8/13 positive and reduces the median signed move to about +0.50 pips. This is not enough to conclude that PPI releases create a reliable CALL edge.

### FOMC statement and minutes
FOMC statements did not show a directional advantage. Minutes showed 6/10 positive at 30 minutes, but removing the largest absolute move changes the 30-minute positive count to 5/9 and median signed move to about +0.40 pips. No reliable direction emerges.

## Binary payout hurdle

At a hypothetical 92% net payout, a simple binary contract needs a win rate above **52.08%** before any execution/friction effects. The directional shares above are **not** binary-option win rates: they measure the sign of a candle-window close-to-open move, not whether an entry at a specific executable quote wins at a specific expiry. No strategy profitability claim is made.

## What this says about the research hypothesis

1. Calendar announcements are precisely timestamped and can be studied ahead of time; the market does not have to wait until a release to begin repricing. However, this study only measures the scheduled release timestamp and does not test pre-release positioning or leakage.
2. “Event day” alone is not a useful direction signal. The event category and context matter.
3. NFP downside skew and PPI upside skew are candidate hypotheses to validate, not signals.
4. Higher activity does not automatically mean higher directional predictability. Several event groups were no more active, or even less active, than matched controls.
5. The next valid test must freeze hypotheses and evaluate on a later holdout period, using explicit entry/expiry conventions, actual payout per observation, and no post-hoc selection of the best horizon.

## Next validation step

Do not integrate these findings into HydraAI signals yet. Next run:
- pre-release windows (-60 to 0 minutes) to test whether the move begins before the release;
- direction conditioned on the pre-event trend and surprise direction (actual vs consensus), where a reliable economic calendar archive is available;
- event-specific 1/3/5-minute entries and 5/10/20-minute expiries with quote-side assumptions and per-trade payout;
- leave-one-month-out or chronological holdout validation, with multiple-testing correction.

## Reproducibility

Script committed alongside this report:
`research/bls_fomc_matched_event_study.py`

Input CSV is in the user's Library and is not copied into this repository. Run:

```bash
python research/bls_fomc_matched_event_study.py /path/to/eurusd_research_clean.csv --out research_output
```

It writes:
- `event_windows.csv`
- `matched_control_windows.csv`
- `event_vs_matched_controls.csv`
- `summary.csv`

No desktop application code, production strategy, or auto-trading behavior was changed.
