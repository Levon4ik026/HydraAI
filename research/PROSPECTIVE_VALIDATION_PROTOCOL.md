# HYDRA — prospective validation protocol (frozen)

**Status:** preregistered protocol; no strategy promotion authorized.  
**Research branch:** `hydra/research-validation`  
**Scope:** EUR/USD only; analysis/simulation only; no order execution, no automated trading, no OTC.

## 1. Objective

Test whether the previously identified New York-session PUT candidate has a repeatable edge on **new, prospectively collected data** that was not used to discover or tune it. Historical TEST results are exploratory and are not confirmatory evidence.

The primary source is the user's own Pocket Option DEMO EUR/USD candle feed. Dukascopy EUR/USD BID may be used as a separately labelled secondary replication only; never concatenate it with Pocket Option candles or treat it as equivalent.

## 2. Frozen strategy definition

The underlying signal generator is unchanged:

- Bollinger Bands: 20 periods, 2 standard deviations, population variance as implemented in the frozen research code.
- Williams %R: 14 periods.
- ADX/DMI: Wilder 14.
- Base PUT signal on a **closed M5 candle i**:
  - previous close is above previous upper Bollinger Band;
  - current close returns below current upper Bollinger Band;
  - Williams %R crosses -20 downward (previous value >= -20, current value < -20);
  - ADX(14) >= 15.
- Candidate context, all evaluated only on candle i or earlier:
  - New York local clock 08:00 inclusive to 13:00 exclusive, using `America/New_York` and daylight-saving rules;
  - ADX(14) >= 25;
  - +DI(14) > -DI(14);
  - close[i] > close[i-12] (positive 12-bar M5 close momentum).
- Direction: PUT only. No CALL trades are part of this candidate.

No thresholds, indicators, time windows, direction, or feature definitions may be altered during the confirmatory run.

## 3. Entry, expiry and trade scheduling

- A signal exists only after M5 candle i is fully closed and validated.
- Simulated entry: open of the immediately following M5 candle (i+1).
- Simulated settlement: close of the fourth M5 candle after signal (i+4), i.e. a 20-minute horizon measured from the next M5 open.
- PUT outcome: WIN if settlement close < entry open; LOSS if settlement close > entry open; DRAW if equal at the stored quote precision.
- One-position rule: after accepting a candidate at index i, do not accept another candidate in that same continuous segment until index i+4. A new signal at i+4 may be accepted because the previous simulated position settles at that candle's close. Do not overlap trade outcome intervals.
- If the next entry candle or any required settlement candle is missing, invalid, stale, or crosses a data-segment boundary, discard the signal as **unsettleable** and log the reason. Do not fill missing candles synthetically.

This is a candle-based research simulation, not a claim about actual Pocket Option fills or payout execution.

## 4. Data collection and integrity

Primary source: Pocket Option DEMO EUR/USD guest feed, stored as timestamped M1 OHLC with UTC timestamps. Preserve original raw CSV and connection log; never overwrite raw files. Record collection start/end, source/platform, symbol, timezone convention, collector version/commit, and any reconnects.

Before building M5:
- validate timestamp uniqueness and ordering;
- validate finite positive OHLC and OHLC consistency;
- report duplicate rows, missing M1 minutes, reconnect gaps, stale/future timestamps, and rejected rows;
- build only complete UTC-aligned M5 bars from five consecutive M1 candles;
- split the series at every missing/incomplete M5 interval; never bridge gaps;
- verify that all indicator warm-up and 12-bar momentum history are inside the same continuous segment.

A dataset is not eligible for the primary analysis if timestamps cannot be unambiguously normalized to UTC, the source cannot be verified as Pocket Option DEMO EUR/USD, or the raw source file/log is unavailable. If feed quality is insufficient, report **data-quality failure**, not a strategy loss or a no-signal result.

Dukascopy data, if used, must have its own report, separate results table and explicit BID-feed limitation.

## 5. Payout and accounting

- Primary reference payout: 92%, matching the current working baseline.
- Report actual displayed Pocket Option payout at each accepted signal when observable. Preserve a timestamped payout log or screenshot/export where possible.
- Primary standardized score: WIN +0.92 units; LOSS -1.00 unit; DRAW 0.
- Also report realized payout sensitivity using the observed payout for each trade if reliable payout observations are available. Do not silently substitute an assumed payout.
- Break-even decisive win rate at 92% payout: 52.0833%.
- Always report W/L/D, decisive win rate W/(W+L), total accepted trades, net units, profit factor, maximum drawdown, maximum consecutive loss streak, and number of skipped/unsettleable signals. Report confidence intervals and sample dates.

## 6. Sample size and analysis plan

- Target: **333 decisive, non-overlapping, settleable candidate trades**. Draws are reported separately and do not count toward the decisive-trade target.
- The 333 target is an approximate exact-binomial design for 80% power to distinguish a 58.9% decisive win probability from the 52.0833% break-even probability at a one-sided 5% significance level, assuming independent outcomes. Market clustering and serial dependence violate that idealized assumption, so this calculation is a planning reference, not a guarantee.
- Do not stop early because interim results look good or bad. Do not repeatedly test significance during collection.
- If 333 decisive trades are not reached within 12 months after the first eligible prospective candle, close the scheduled collection window and label the result **underpowered / inconclusive**. Do not lower the sample target after seeing results.
- Final primary test: exact one-sided binomial test against p0 = 1/(1+0.92), reported alongside a 95% Wilson interval. Also calculate a predeclared 5-trading-day block bootstrap interval for mean daily net units to expose sensitivity to serial clustering. The binomial test alone is not sufficient for a promotion decision.
- No parameter sweeps, subgroup mining, threshold adjustment, or new filters on the prospective sample. Any later exploratory analysis must be clearly separated and cannot replace the primary result.

## 7. Predeclared interpretation / decision rules

The candidate is **not promoted** merely because net units are positive or observed WR exceeds break-even.

A result may be described as *prospectively supportive* only if:
1. the required 333 decisive trades are collected with acceptable source/data integrity;
2. decisive WR exceeds 52.0833% and the one-sided exact binomial p-value is < 0.05;
3. net units at standardized 92% payout are positive;
4. the 5-day block-bootstrap 95% interval for mean daily net is above zero;
5. no material data-quality, timestamp, quote-source, or settlement ambiguity invalidates the sample.

If any criterion fails, report the exact outcome as negative, inconclusive, or data-quality-limited. Even if all pass, this only supports further paper/demo validation; it does not authorize live trading or automatic execution.

## 8. Reporting template

Final report must include:
- collection dates, platform/source, symbol, raw M1 rows, complete M5 bars, segments, gaps, duplicates, stale/future/rejected rows;
- collector version/commit and file hashes;
- frozen parameter checksum or source commit;
- accepted candidate signals, skipped/unsettleable signals and reasons;
- W/L/D, decisive WR, Wilson 95% CI, exact binomial p-value;
- net units, PF, max drawdown, max loss streak, average daily net, block-bootstrap 95% CI;
- observed payout distribution and 85%/90%/92% standardized sensitivity;
- chronological monthly breakdown, marked descriptive only;
- deviations from this protocol (ideally none);
- explicit statement that no orders were opened.

## 9. Governance

This document freezes the prospective test only. Research changes stay on `hydra/research-validation`. Do not modify `main`, merge/promote to `hydra/stabilization`, or alter local Windows project files without explicit user approval. Production strategy remains unchanged.
