# Broad Macro & Market Event Study — First M1 Replay (2026-10)

**Branch:** `hydra/research-validation`  
**Data:** repository file `eurusd_history_extended.csv`  
**Blob SHA:** `ee5f264997f94553818d95ced1d3b11fa58737e1`  
**Coverage:** 2026-10-07 04:31 UTC — 2026-10-28 01:19 UTC  
**Rows:** 30,048 one-minute candles  
**Instrument:** EUR/USD  
**Status:** exploratory event-window replay; not a trading strategy or proof of causality.

## 1. Purpose and scope

The research scope is broader than Treasury bond payments. This first replay maps several recurring, timestamped event families onto the available EUR/USD M1 history:

1. high-importance US macro releases (CPI, PPI, import/export prices);
2. recurring Federal Reserve balance-sheet/liquidity publication (H.4.1);
3. CFTC Commitments of Traders publication;
4. other scheduled BLS releases in the sample (state employment and weekly earnings).

This is a first feasibility test, not a complete market-event database. The current candle sample covers only about three weeks, and it cannot support robust multi-year conclusions.

## 2. Official calendar validation

The BLS 2026 release calendar lists:
- Oct 14, 08:30 US Eastern — September CPI;
- Oct 15, 08:30 US Eastern — September PPI;
- Oct 16, 08:30 US Eastern — September import/export prices;
- Oct 20, 10:00 US Eastern — state employment;
- Oct 21, 10:00 US Eastern — usual weekly earnings;
- Oct 28, 10:00 US Eastern — metropolitan employment and business employment dynamics.

Source: https://www.bls.gov/schedule/2026/

The Federal Reserve says H.4.1 is generally released Thursdays at 4:30 p.m. Eastern, subject to holiday shifts. Dates overlapping this sample include Oct 8, 15 and 22.
Source: https://www.federalreserve.gov/releases/h41/

The CFTC says COT reports are generally released Fridays at 3:30 p.m. Eastern and use position data from the preceding Tuesday. Sample dates: Oct 9, 16 and 23.
Source: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm

The Daily Treasury Statement summarizes cash and debt operations, including operating cash, deposits/withdrawals and public debt transactions; it is available by 4 p.m. the following business day. This is a useful source for a future liquidity-flow event panel, but publication time is not the same as the underlying cash-flow time.
Source: https://fiscal.treasury.gov/accounting/daily-treasury-statement

Eurostat's release calendar covers euro-area inflation, GDP/employment, industrial production, trade, unemployment, government debt and other indicators; it uses Luxembourg local time. It should be joined to the same event database in the next phase.
Source: https://ec.europa.eu/eurostat/web/main/news/euro-indicators/release-calendar

## 3. Method

- Convert US Eastern release times to UTC using the correct October daylight-saving offset (UTC−4).
- For each event, calculate complete M1 windows immediately before and after the scheduled release.
- Path activity = sum of absolute close-to-close changes, in pips.
- Range = maximum high minus minimum low, in pips.
- Signed return = last close minus first candle open, in pips.
- For the three 08:30 ET BLS releases, compare the event dates with all other complete dates at the same 12:30 UTC clock time in the available sample.
- Missing/incomplete windows are excluded rather than filled.

Important limitation: this is a small, unadjusted control group. It is not matched for weekday, pre-event volatility, concurrent news, trend, spreads, liquidity or market regime. Events close together may overlap in their wider windows.

## 4. Main measured result: 08:30 ET BLS release cluster

Three release dates were tested at 12:30 UTC:
- Oct 14 — CPI;
- Oct 15 — PPI;
- Oct 16 — import/export prices.

Median results across the three event dates versus the other 18 dates with complete windows:

| Window | Event median path | Control median path | Event median range | Control median range |
|---|---:|---:|---:|---:|
| 15 min before | 13.6 | 8.55 | 4.0 | 5.3 |
| 15 min after | 56.9 | 13.1 | 25.2 | 5.45 |
| 30 min before | 23.4 | 21.15 | 9.1 | 9.0 |
| 30 min after | 92.5 | 24.45 | 25.2 | 7.6 |
| 60 min before | 50.6 | 43.2 | 11.1 | 9.4 |
| 60 min after | 140.6 | 52.6 | 26.1 | 9.95 |

The post-release path median was about 4.3x the control median in the first 15 minutes and 3.8x in the first 30 minutes. The median post-release range was also much larger.

**But the result is dominated by one observation: Oct 14 CPI.** Its post-release signed return was −44.4 pips in five minutes, −62.4 pips in 15 minutes, and −69.8 pips in 60 minutes. By comparison:
- Oct 15 PPI: +9.7 pips in 15 minutes, +5.4 pips in 60 minutes;
- Oct 16 import/export prices: −5.9 pips in 15 minutes, −7.2 pips in 60 minutes.

Thus the event cluster shows a strong volatility association in this tiny sample, but it does **not** establish a consistent direction or a generalizable entry rule. It is an example of why event categories must be separated by release type and surprise magnitude rather than pooled blindly.

## 5. Other event families: first checks

### Federal Reserve H.4.1 — 4:30 p.m. ET (20:30 UTC)

Three sample dates (Oct 8, 15, 22) were inspected. Post-release 15-minute path activity was 9.1, 7.1 and 6.2 pips respectively; 60-minute path activity was 70.9, 34.7 and 36.0 pips. The first 15-minute returns were −1.1, +3.1 and −0.8 pips.

This does not show a stable direction or an obvious immediate impulse. Three observations and no weekday-matched non-event controls are insufficient to infer either an effect or no effect.

### CFTC COT — 3:30 p.m. ET (19:30 UTC)

Three Friday dates (Oct 9, 16, 23) were inspected. Post-release 15-minute path activity was 6.9, 9.9 and 5.4 pips; post-release 60-minute path activity was 28.4, 33.0 and 23.3 pips. Fifteen-minute signed returns were −0.9, −2.5 and +1.0 pips.

No consistent directional response is visible in these three observations. The report reflects positions as of Tuesday, so the publication is a positioning-information event, not a real-time measure of Friday order flow.

### Other BLS 10:00 ET releases

Oct 20 state employment and Oct 21 weekly earnings were inspected at 14:00 UTC. Their post-release 15-minute path activity was 15.7 and 18.4 pips; 60-minute path activity was 95.7 and 55.5 pips. Two dates do not provide a meaningful event study.

## 6. What this establishes — and what it does not

**Established from the current data:**
- The available M1 history contains a very large EUR/USD move immediately after the scheduled Oct 14 CPI release.
- Pooling Oct 14–16 BLS releases produces materially higher post-release path/range than other 12:30 UTC windows in this short sample.
- The other inspected event families do not show a clear, repeatable directional response in the few observations available.

**Not established:**
- that all CPI releases create similar movement;
- that event dates predict direction;
- that the movement can be captured after spread, payout, latency and execution constraints;
- that H.4.1 or COT have no effect;
- that the event-day pattern is causal.

The October sample is not suitable for strategy validation. The Oct 14 CPI observation is an outlier and could dominate all pooled statistics.

## 7. Next research steps

1. Extend EUR/USD M1 history to at least 3–5 years, ideally BID and ASK separately.
2. Build a timestamped event ledger with actual scheduled and revised release times, event family, country/currency, importance and actual-vs-consensus surprise where available.
3. Keep separate panels for US CPI, PCE, NFP, FOMC, ECB, Eurostat inflation/GDP/PMI, Treasury auctions/settlements/cash flows, Fed liquidity releases, CFTC COT, options expiries and month/quarter-end.
4. For every family, use weekday/session/pre-volatility matched controls and robust statistics (median, quantiles, bootstrap confidence intervals), not only pooled averages.
5. Split immediate reaction (0–5, 5–15, 15–30, 30–60, 60–120 min) from pre-event drift and session-level effects.
6. Freeze hypotheses on one period and validate on a later untouched period. Only after that test whether any signal has positive expectancy at realistic Pocket Option payouts and execution assumptions.

## 8. Research decision

**Priority for the next quantitative replay: US CPI and NFP separately, then FOMC/ECB rate decisions, then Eurostat inflation and PMI.** These are clearly timestamped and directly relevant to interest-rate expectations and EUR/USD. Continue Treasury cash-flow work as a distinct event family rather than treating it as the whole macro picture.

No trading signal is approved by this report.
