# HYDRA Time Machine — research design v1

**Status:** design frozen for implementation/testing; research only.  
**Branch:** `hydra/research-validation`  
**Market:** EUR/USD, M1 source aggregated to complete M5 bars.  
**Execution:** analysis/simulation only; no orders, no auto-trading, no OTC.

## 1. Purpose

Adapt the useful idea from Jake Schincariol's Claude `trader-timemachine`: replay possible paths from a proposed entry, and compare simulation probabilities with the actual historical record.

Do not copy its stock-market assumptions or treat 10,000 Monte Carlo paths as 10,000 independent observations. Hydra's target is a fixed-expiry binary outcome, not a stop/target bracket trade.

The Time Machine is a **diagnostic and calibration tool**, not a signal generator and not a proof of edge. It must never upgrade a WAIT to CALL/PUT by itself.

## 2. Important differences from the reference implementation

The reference implementation samples individual bars from similar time-of-day slots. That is simple and useful for visual scenario generation, but it can break serial dependence between candles. Hydra v1 therefore uses a **contiguous moving-block bootstrap**:

- Sample consecutive blocks of M5 returns, not isolated candles.
- Keep each sampled block within one valid, gap-free segment.
- Preserve the observed order inside each block.
- Sample only from data strictly earlier than the forecast timestamp.
- Match the forecast's UTC time-of-day slot within a predeclared tolerance.
- Match a volatility regime using a trailing, causal volatility measure whose thresholds are estimated only from the historical pool available at that forecast timestamp.
- Do not sample any bar that overlaps the forecast's entry or settlement window.

This preserves short-run clustering better than independent-bar sampling, but still cannot reproduce every market dependency or news shock.

## 3. Forecast contract

Input for each forecast:
- EUR/USD symbol and verified source label;
- signal timestamp after a fully closed M5 bar;
- direction CALL or PUT;
- simulated entry at next M5 open;
- fixed expiry in M5 bars (1, 2, 3, 4, 6 or 12);
- frozen payout assumption (92% standard baseline; actual payout may be logged separately);
- historical lookback limited to the 60 most recent eligible trading dates before the signal;
- deterministic random seed and simulation count.

Output:
- simulated probability of WIN / LOSS / DRAW at expiry;
- expected standardized net units at 92% payout;
- Monte Carlo standard error / interval for the simulated probability (explicitly labelled simulation uncertainty, not market confidence);
- historical analogue count and realized W/L/D for the same time bucket and volatility regime;
- sample dates, seed, block length, pool size, data gaps, and exclusions;
- a clear warning when the historical pool is too small or regime matching is unavailable.

For binary settlement, only the simulated expiry price determines WIN/LOSS/DRAW. Intrabar stop/target logic from the stock-market skill is not relevant to this product.

## 4. Sampling algorithm

For each forecast:
1. Build log-return increments from complete M5 OHLC bars. The first increment after a simulated entry uses `log(close/open)`; subsequent increments use `log(close_t/close_(t-1))`.
2. Restrict candidate history to the 60 most recent eligible trading dates strictly before the forecast.
3. Exclude every segment boundary, incomplete bar, invalid quote, and any candidate block crossing a gap.
4. Filter candidate block starts by time-of-day proximity and causal volatility-regime compatibility.
5. Draw contiguous blocks of a predeclared length (primary: 3 M5 bars; sensitivity: 1, 6 bars) until the forecast horizon is filled.
6. Apply the sampled log returns to the simulated entry price.
7. Settle CALL/PUT at the expiry close using the same quote precision and tie rule as the backtest.
8. Repeat with a fixed seed. Run multiple seeds as a sensitivity check; do not choose the seed that produces the best result.

No future data, current forming candle, or outcome label may enter the forecast pool or its regime classification.

## 5. Validation design

The Time Machine itself must be tested as a forecasting model, not just judged by attractive sample paths.

- Use the existing chronological TRAIN / VALIDATION / TEST split.
- Select strategy variants on VALIDATION only, with the selection rule declared before opening TEST results.
- Freeze selected strategy IDs, expiry, portfolio conflict policy, block length, time-of-day tolerance, regime definition, lookback, and random seed before TEST evaluation.
- Forecast each accepted TEST trade using only prior history available at that timestamp (walk-forward).
- Compare predicted probabilities with actual binary outcomes using Brier score, log loss, calibration bins, and reliability plots.
- Compare the bootstrap forecast to simple baselines: unconditional historical win rate, same time-of-day only, and same volatility regime only.
- Report results by direction, expiry, and regime only as predeclared descriptive slices.
- Include W/L/D, decisive WR, net units at 92%, PF, max drawdown, max consecutive losses, trades per 20 weekdays, and the fraction of signals filtered by insufficient pool quality.

The existing Dukascopy BID history has already been explored repeatedly. Any result on it remains **exploratory**, even with a chronological split. It is not a pristine confirmatory holdout and is not Pocket Option quote data.

## 6. Acceptance criteria before considering integration

Do not integrate into Hydra Desktop unless all are true:
- no look-ahead or gap-crossing tests fail;
- results are deterministic for a fixed seed;
- block bootstrap beats or materially complements the simple baselines on out-of-sample Brier/log-loss, not just trade win rate;
- probability calibration is acceptable and stable across chronological slices;
- forecast output is fast enough for M1/M5 use;
- the filter does not create misleading confidence or simply suppress almost every signal;
- prospective Pocket Option DEMO data confirms the behavior separately.

Even if accepted, the Time Machine remains advisory. It can lower confidence or return INSUFFICIENT_DATA; it cannot autonomously create a CALL/PUT.

## 7. Required engineering tests

- fixed-seed reproducibility;
- no future timestamps in the pool;
- no block crosses a segment gap;
- no block includes the forecast entry/settlement interval;
- no incomplete M5 bars;
- exact settlement/tie behavior;
- small-pool fallback to INSUFFICIENT_DATA;
- synthetic series with known return distribution;
- high-volatility and low-volatility regime separation;
- probability bounds and sum-to-one;
- no division-by-zero or NaN propagation.

## 8. Provenance

Reference concept: `Jakeschincariol/day-trader-skill`, specifically `trader-timemachine`. Its Monte Carlo simulation is useful as an architectural reference; its stock-specific 60-day intraday pool and independent-bar sampling are not copied as-is.

No production code, local Windows files, stabilization branch, or main branch may be changed under this design.
