# FX fixing and session-reversal discovery — preregistration v1
Date frozen: 2026-11-15
Branch: hydra/research-validation
Status: preregistration; no performance result is implied.

## Purpose and deduplication
This is a new research family based on published FX benchmark-fixing reversal evidence and the daily/weekly abnormal-move reversal literature. The existing candidate registry and work logs were checked before formalization. The registry already contains generic session-clock/volatility audits, a NY cash-open downside-skew lead, mean-reversion work, previous-day/week level candidates, and impulse-reversal candidates. Those are not renamed here. No fixing-time strategy or NY-17:00 completed-session shock-reversal candidate was found in the checked registry/work logs. The NY cash-open lead is excluded from this candidate set.

## Frozen candidates
All use EUR/USD M1 BID bars, exact timestamps, next eligible M1 open, 60-minute expiry (entry bar open through close of entry+59 minute bar), and no trade if any required minute is missing. A signal is causal and known before entry. The same event timestamps are evaluated with the opposite direction as a matched continuation control.

1. FXFIX-TOKYO-FADE-60
   - Time zone: Asia/Tokyo; fixing 09:55 local, Monday–Friday.
   - Pre-fix window: exactly 240 minutes ending at the fixing time.
   - If pre-fix EUR/USD return is positive, PUT; if negative, CALL.
   - Entry at the fixing-time M1 open; expiry 60 minutes.
2. FXFIX-ECB-FADE-60
   - Time zone: Europe/Berlin; ECB reference fixing 14:15 local, Monday–Friday.
   - Pre-fix window: 07:00 local to 14:15 local.
   - Fade the completed pre-fix EUR/USD return; entry at 14:15 local; expiry 60 minutes.
3. FXFIX-LONDON-FADE-60
   - Time zone: Europe/London; London fixing 16:00 local, Monday–Friday.
   - Pre-fix window: 07:00 local to 16:00 local.
   - Fade the completed pre-fix EUR/USD return; entry at 16:00 local; expiry 60 minutes.
4. NY17-DAILY-SHOCK-FADE-60
   - A session is 17:00 America/New_York to 17:00 the next local calendar day, starting Sunday–Thursday.
   - A session is valid only with exact start and end-1-minute bars, at least 99% minute coverage, and no within-session gap above 5 minutes.
   - After at least 20 preceding valid sessions, signal if the absolute completed-session log return is at least 1.5 times the mean absolute return of the preceding 20 sessions (current session excluded).
   - Fade the completed session direction at the next 17:00 New York open; expiry 60 minutes.
5. NY17-WEEKLY-SHOCK-FADE-60
   - A week is Sunday 17:00 America/New_York to Friday 17:00 America/New_York.
   - Require exact start and Friday end-1-minute bars, at least 99% coverage, and no within-week gap above 5 minutes.
   - After at least 13 preceding valid weeks, signal if the absolute completed-week log return is at least 1.0 times the mean absolute return of the preceding 13 weeks (current week excluded).
   - Fade the completed week direction at the next Sunday 17:00 New York open; expiry 60 minutes.

## Accounting and controls
- WIN = +0.92u, LOSS = -1u, DRAW = 0u; payout sensitivity must also show 50/60/70/80/85/90/92/95/100%.
- Break-even decisive WR at 92% payout = 52.0833%.
- Report N, W/L/D, decisive WR and Wilson 95% interval, net/ROI/expectancy, profit factor, maximum drawdown, longest losing streak, active days, trades per active day, signal/WAIT share, monthly stability, data coverage, gaps, exclusions, and a day-cluster bootstrap interval for WR/net.
- Matched continuation control uses the exact same entry timestamps and expiry, but the direction is the opposite of the candidate's fade direction. Do not compare against a different timestamp schedule.
- No pooling across candidates.

## Data and split policy
- Source: Dukascopy EUR/USD M1 BID. It is not Pocket Option executable pricing.
- Download 2024-01-01 through the day after the run date; record exact coverage, raw/valid/invalid/duplicate counts, gaps, continuity segments, raw CSV SHA-256, script SHA-256, and this protocol SHA-256.
- Chronological calendar split: first 60% TRAIN, next 20% VALIDATION, final 20% TEST, based on full data coverage dates. Purge trades whose settlement crosses a split boundary.
- This underlying historical period has been used by other HydraAI research screens. Even though these exact fixing/session rules were not found in the registry, label historical TEST as previously inspected-source / exploratory, not pristine independent confirmation.
- No threshold or direction may be changed after inspecting VALIDATION/TEST. No parameter sweep is allowed in this run.
- Small samples are descriptive only. A preliminary lead requires at least 30 trades in both VALIDATION and TEST, positive net at 92% in both, and decisive WR above 52.0833% in both. This is a screening rule, not confirmation. Any passing result still requires prospective forward validation and Pocket Option DEMO quote/settlement comparison.
- A five-candidate batch is not filled with weak or under-sampled rows. Report only candidates that pass the primary screen as preliminary leads; retain all failed rows in the research artifact with exact reasons.

## Literature motivating hypotheses (not proof of profitability)
- Krohn, Mueller & Whelan, Journal of Finance 2024, “Foreign Exchange Fixings and Returns around the Clock,” DOI 10.1111/jofi.13306. The paper documents USD appreciation before Tokyo/ECB/London fixes and reversal thereafter using G9 high-frequency data from 1999–2019.
- Breedon & Ranaldo, “Intraday Patterns in FX Returns and Order Flow,” Journal of Money, Credit and Banking 2013, DOI 10.1111/jmcb.12032. It documents time-of-day effects and order-flow relationships.
- Caporale & Plastun, “Daily abnormal price changes and trading strategies in the FOREX,” DOI 10.1108/JES-11-2019-0503. The paper reports next-day opposite-direction movement after abnormal daily price changes. The exact HydraAI rules above are new operational hypotheses and are not claimed to replicate the paper's original strategy.

## Limitations
Dukascopy BID candles omit executable spread, Pocket Option quote construction, latency, payout variation and platform settlement details. M1 candles do not reveal intraminute path. Wilson intervals assume independent outcomes; day-cluster bootstrap only partially addresses dependence. Historical selection across many prior HydraAI research families creates broader multiple-testing risk.
