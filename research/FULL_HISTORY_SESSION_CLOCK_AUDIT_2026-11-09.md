# HYDRA — full-history EUR/USD intraday clock-time audit

Date: 2026-11-09  
Branch: `hydra/research-validation`  
Dataset: `eurusd_research_clean.csv`, 486,488 M1 rows, 2025-07-21 15:11 UTC — 2026-11-05 16:08 UTC.  
Dataset SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.

## Executive result

The longer history changes the picture from the earlier three-week sample. The most active recurring 30-minute window in the covered weekday hours is around **17:00 London / 12:00 New York**, not the London 08:00 open or the generic US 08:30 data-release clock.

There is also a descriptive downside skew in the 30 minutes after the New York 09:30 cash open. It is a candidate for a carefully frozen follow-up, not an approved PUT signal. No CALL/PUT strategy or Desktop logic is changed.

## 1. Data integrity and coverage

- 486,488 rows; 0 duplicate timestamps.
- 0 non-increasing timestamp steps.
- 67 gaps larger than one minute; 193,250 absent minute slots across those gaps. These include closed-market periods and long capture gaps, so they are not interpreted as 193,250 isolated feed failures.
- 2,739 weekend rows; excluded from session calculations.
- 0 invalid OHLC rows.
- Absolute open-to-previous-close discontinuity: 133 rows >2 pips, 63 >5 pips, 44 >10 pips.
- M1 high-low range: median 1.1 pips; p90 2.5; p99 5.2; p99.9 10.6.

Each 30-minute observation below requires at least 25 valid one-minute close-to-close transitions. The two halves contain 159 and 179 eligible weekdays respectively for most bins.

## 2. Method

- UTC timestamps were converted independently to Europe/London and America/New_York using DST-aware IANA time zones.
- For each local date and 30-minute bin: path = sum of absolute close-to-close changes, range = max(high) − min(low), signed return = last close − first open.
- A close-to-close step contributes to path only when its timestamps are exactly one minute apart.
- Weekends excluded. Stability split: before/after 2026-03-01.
- This is a clock-time activity study, not a news-event causal study and not a binary-options backtest.

## 3. Highest activity windows

### London local time

| Local bin | Eligible days | Median path | Median 30m range | Median signed return |
|---|---:|---:|---:|---:|
| 17:00 | 338 | 35.75 pips | 12.65 pips | −0.20 pips |
| 17:30 | 338 | 34.70 | 12.35 | +0.05 |
| 16:30 | 338 | 34.35 | 11.75 | +0.65 |
| 15:30 | 338 | 33.15 | 11.8 | +0.45 |
| 16:00 | 339 | 31.20 | 11.0 | −0.10 |
| 10:00 | 338 | 28.75 | 10.2 | +0.25 |

Quietest covered London bins were 06:30–07:30, with median 30-minute path around 12.7–13.4 pips.

### New York local time

| Local bin | Eligible days | Median path | Median 30m range | Median signed return |
|---|---:|---:|---:|---:|
| 12:00 | 338 | 35.80 pips | 12.85 pips | approximately 0 |
| 12:30 | 338 | 34.90 | 12.5 | +0.60 |
| 11:30 | 338 | 34.50 | 11.9 | +0.40 |
| 10:30 | 338 | 32.70 | 12.0 | +0.20 |
| 11:00 | 339 | 31.10 | 11.0 | −0.30 |
| 13:00 | 338 | 31.00 | 11.2 | −0.70 |

The highest New York bins map to the same clock period as the London late-afternoon peak. This is a volatility/activity cluster, not a directional signal.

## 4. Stability across the sample

Selected 30-minute bins, split at 2026-03-01:

| Local time | Earlier median path | Later median path | Earlier range | Later range |
|---|---:|---:|---:|---:|
| London 08:00 | 17.2 | 13.6 | 6.0 | 5.0 |
| London 10:00 | 30.6 | 25.5 | 11.0 | 9.1 |
| London 16:00 | 32.2 | 30.1 | 11.8 | 10.5 |
| London 17:00 | 39.5 | 32.9 | 13.7 | 11.1 |
| New York 08:30 | 21.3 | 20.2 | 7.2 | 7.5 |
| New York 09:30 | 26.9 | 23.9 | 9.2 | 8.8 |
| New York 12:00 | 39.5 | 33.0 | 13.8 | 11.25 |

The late-afternoon activity peak persists in both halves, but its median path falls by roughly 17% from the earlier to later period. The same general reduction appears at several other active times. That is evidence of non-stationarity in the volatility profile, not proof of a specific causal change.

## 5. Fixed clock windows around commonly watched times

These are all eligible weekdays, not dates selected because a release actually occurred.

| Local anchor | Window | Days | Median path | Median range | Median signed return | Positive-day share |
|---|---|---:|---:|---:|---:|---:|
| London 08:00 open | PRE | 338 | 13.35 | 4.60 | +0.25 | 54.4% |
| London 08:00 open | POST | 338 | 15.20 | 5.55 | +0.10 | 50.6% |
| London 17:00 close | PRE | 338 | 34.35 | 11.75 | +0.70 | 52.7% |
| London 17:00 close | POST | 338 | 35.75 | 12.65 | −0.30 | 46.7% |
| NY 08:30 data time | PRE | 338 | 21.80 | 7.75 | −0.20 | 48.2% |
| NY 08:30 data time | POST | 338 | 20.80 | 7.30 | +0.15 | 51.8% |
| NY 09:30 cash open | PRE | 338 | 22.15 | 8.10 | +0.10 | 50.3% |
| NY 09:30 cash open | POST | 338 | 25.55 | 9.10 | −0.80 | 41.4% |
| NY 12:00 midday | PRE | 338 | 34.50 | 12.00 | +0.40 | 50.9% |
| NY 12:00 midday | POST | 338 | 35.80 | 12.85 | −0.05 | 48.5% |
| NY 14:00 | PRE | 338 | 27.50 | 9.20 | −0.60 | 45.9% |
| NY 14:00 | POST | 338 | 24.20 | 8.70 | −0.20 | 47.6% |

### New York 09:30 downside observation

The 30-minute post-open window had a negative median signed return and only 41.4% positive days across 338 weekdays. In the two chronological halves:

- Earlier: 73 positive / 85 negative days; median signed return −0.4 pips.
- Later: 67 positive / 108 negative days; median signed return −1.5 pips.

This is worth testing further, but it is a post-hoc time slice. It may reflect the composition of news days, prior overnight movement, broader market regime, or data-source/session effects. It does not establish a 5-minute PUT edge, and a 30-minute direction result cannot be translated directly into a 5-minute binary-options win rate.

## 6. What this tells us about news research

A generic 08:30 New York clock-time average does not show a weekday-wide volatility burst. That is not evidence that CPI, NFP, or other scheduled releases have no effect: most weekdays do not contain those releases. Actual release dates must be isolated and compared with same-weekday, same-month non-event controls.

This supports a more rigorous event design:
1. Build the exact release-date/time ledger for CPI, NFP, PPI, FOMC, ECB, PMI, and other predeclared events.
2. For each event, measure pre-event activity separately from 0–5, 5–15, 15–30, and 30–60 minutes after release.
3. Match control dates by weekday, month/quarter, session, and pre-event volatility.
4. Separate volatility expansion from direction; score binary outcomes only with the actual entry/expiry convention and payout.
5. Use day-block uncertainty and report all event families tested, not only the strongest.

## 7. Decision

- No clock-time CALL/PUT filter is approved.
- Preserve two hypotheses for a predeclared follow-up: (a) elevated activity around 17:00 London / 12:00 New York; (b) possible downside asymmetry after the NY 09:30 cash open.
- Next test should use same-weekday/month controls, day-block uncertainty, fixed 5m/20m settlement outcomes, and actual payout. Any candidate then needs prospective Pocket Option DEMO confirmation.
- No Desktop code, production math, or automatic-trading behavior changed.

## Reproducibility

Script: `research/full_history_session_clock_audit.py`  
Run with:

```bash
python research/full_history_session_clock_audit.py --data eurusd_research_clean.csv
```

The source CSV is in the user's Library and is not copied into the repository by this report.
