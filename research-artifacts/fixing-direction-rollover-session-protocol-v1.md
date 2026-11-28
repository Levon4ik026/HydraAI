# FX fixing direction and rollover-excluded session reversal — preregistration v1
Frozen: 2026-11-15
Branch: hydra/research-validation
Status: new hypotheses; no performance result implied.

## Deduplication and distinction from screen 1
The prior screen tested an adaptive fade of the observed pre-fix EUR/USD move, a 4-hour Tokyo window, and NY 17:00-to-17:00 sessions under a 99% coverage rule. Those exact rules are frozen and not changed. This protocol tests distinct rules:
- a literature-directed EUR/USD CALL after a benchmark fix only when EUR/USD declined during the published pre-fix window (USD-strength precondition);
- a Tokyo pre-window anchored to 17:00 New York, not a fixed four-hour lookback;
- rollover-excluded NY sessions (18:00 to 17:00) to avoid requiring M1 quotes during the daily market break;
- a new, fixed shock threshold for daily and weekly session reversals.

No prior candidate in CANDIDATE_REGISTRY or the inspected work logs uses these exact rules.

## Frozen candidate families
Instrument/source: EUR/USD M1 BID from Dukascopy. All features are completed before entry. Entry is at the exact next eligible M1 open. Expiry candidates are 5, 10, 15, 20, 30 and 60 minutes. For every expiry, settlement is the close of the M1 bar timestamped entry+expiry-1 minute; all required M1 bars must be present. The expiry is selected using TRAIN only, then frozen for VALIDATION/TEST.

1. FXFIX-TOKYO-PREFIX-USD-REV-CALL
   - Fix: 09:55 Asia/Tokyo, Monday–Friday.
   - Pre-window begins at 17:00 America/New_York on the New York local date corresponding to the Tokyo fixing instant, and ends at the fixing instant.
   - Signal only if the completed pre-fix EUR/USD log return is negative (USD strengthened); direction is CALL after the fix. Otherwise WAIT.
2. FXFIX-ECB-PREFIX-USD-REV-CALL
   - Fix: 14:15 Europe/Berlin, Monday–Friday.
   - Pre-window: 07:00–14:15 Europe/Berlin.
   - Signal only if completed pre-fix EUR/USD log return is negative; CALL after the fix. Otherwise WAIT.
3. FXFIX-LONDON-PREFIX-USD-REV-CALL
   - Fix: 16:00 Europe/London, Monday–Friday.
   - Pre-window: 07:00–16:00 Europe/London.
   - Signal only if completed pre-fix EUR/USD log return is negative; CALL after the fix. Otherwise WAIT.
4. NY18-DAILY-SHOCK-FADE-60
   - Completed NY session: 18:00 America/New_York to 17:00 the next local calendar day, starting Sunday–Thursday. This deliberately excludes the 17:00–18:00 daily rollover interval.
   - Require exact session start and end-1-minute bars, >=99% minute coverage, and no within-session gap >5 minutes.
   - After 20 preceding valid sessions, signal when absolute current session log return >=1.0x the mean absolute return of the preceding 20 valid sessions (current excluded). Fade the completed session direction at the next 18:00 NY session open.
5. NY18-WEEKLY-SHOCK-FADE-60
   - Completed NY week: Sunday 18:00 America/New_York to Friday 17:00 America/New_York.
   - Require exact endpoints, >=95% minute coverage, and no within-week gap >65 minutes. The 65-minute limit explicitly permits the expected daily rollover closure, but not a weekend bridge.
   - After 13 preceding valid weeks, signal when absolute current week log return >=0.75x the mean absolute return of the preceding 13 valid weeks (current excluded). Fade the completed week direction at the next Sunday 18:00 NY open.

## TRAIN-only expiry selection
For each candidate family, evaluate only the six predeclared expiry values on TRAIN. A variant is eligible for selection only if TRAIN N>=30, decisive WR exceeds the 92%-payout break-even 52.0833%, and TRAIN net units are positive. Select the expiry with the highest Wilson 95% lower bound; tie-break by higher TRAIN net units, then shorter expiry. If no expiry qualifies, select none. Do not use VALIDATION or TEST to choose expiry, threshold, direction, time window, or other rule.

## Evaluation and controls
- WIN +0.92u, LOSS -1u, DRAW 0u; report payout sensitivity 50/60/70/80/85/90/92/95/100%.
- Report N, W/L/D, decisive WR, Wilson 95% interval, net/ROI/expectancy, profit factor, maximum drawdown, longest losing streak, active days, trades per active day, signal/WAIT share, monthly stability, and day-cluster bootstrap interval.
- Matched control: opposite direction at the exact same entry timestamps and prices (PUT control for fixing CALL; continuation control for daily/weekly fade).
- No pooling across candidate families.
- Primary pass: selected expiry must have at least 30 trades in both VALIDATION and TEST, positive net at 92% in both, and decisive WR >52.0833% in both. Passing remains a preliminary lead, not confirmation.

## Data and limitations
- Download 2024-01-01 through the day after the run date; record coverage, raw/valid/invalid/duplicate rows, gaps, continuity segments and SHA-256.
- Chronological calendar split: first 60% TRAIN, next 20% VALIDATION, final 20% TEST. Purge outcomes crossing split boundaries.
- This underlying historical period has been used by other HydraAI screens. Label TEST as previously inspected-source / exploratory, not pristine independent confirmation.
- Dukascopy BID is not Pocket Option executable pricing. Spread, quote construction, platform payout, latency and settlement are not modeled.
- Wilson intervals assume independent trades; day-cluster bootstrap only partially addresses dependence. Multiple candidate families and prior HydraAI searches create broader selection risk.

## Literature motivation
Krohn, Mueller & Whelan, Journal of Finance 2024, “Foreign Exchange Fixings and Returns around the Clock,” DOI 10.1111/jofi.13306, documents USD appreciation before Tokyo/ECB/London fixes and depreciation thereafter in high-frequency G9 data. This motivates a conditional post-fix EUR/USD CALL when the pre-fix EUR/USD return is negative; the paper is not evidence that this exact binary rule is profitable.
