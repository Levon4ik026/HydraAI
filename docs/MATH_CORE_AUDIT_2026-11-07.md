# HydraAI — audit of the mathematical core (2026-11-07)

## Scope and safety

This is a research audit of the historical backtest code. It does not approve a strategy for live use and does not change the manual-only / no-auto-trading rule. The audit is based on the current `hydra/stabilization` source plus the latest indicator-screening report committed to `main` on 2026-11-06.

## Findings in `hydra/stabilization`

### 1. Payout is hard-coded to 80%

The following scripts use a fixed `PAYOUT = 0.80`:
- `backtest.py`
- `backtest_filtered.py`
- `backtest_large.py`
- `backtest_v3.py`
- `random_baseline.py`

This makes their profit results unsuitable as a current estimate when the observed Pocket Option payout is closer to 92% and varies over time. The engine must support either a payout scenario supplied at run time or a per-entry payout series/column. A single fixed payout must be clearly labelled as a scenario, not as observed execution data.

### 2. Indicators in `backtest_v3.py` cross data gaps

`load_data()` calculates EMA20, EMA50 and RSI14 over the entire sorted dataframe. Only later does the trade loop reject an interval containing a gap. As a result, indicator state is still carried across a discontinuity and contaminates signals after the gap.

Correct behaviour: split the history into continuous one-minute segments first; calculate EMA/RSI independently inside each segment; enforce warm-up after each segment reset; and reject any trade whose signal-to-settlement interval crosses a gap.

### 3. Gap handling is inconsistent between backtest versions

- `backtest_v3.py` rejects some trade intervals containing a gap, but does not reset indicators at segment boundaries.
- `backtest_large.py` reports gaps but still calculates row-based expiries and does not reject trades crossing them.
- `backtest.py` and `backtest_filtered.py` do not enforce continuous-minute intervals.

A horizon of N candles must only be treated as N minutes when all required timestamps are consecutive.

### 4. Directional simulations need one shared position timeline

`backtest_v3.py` runs CALL and PUT simulations separately. That can allow opposite-direction trades to overlap in the combined strategy even though the report describes sequential, non-overlapping trades. The corrected engine should schedule both directions through one shared trade loop and only then report CALL/PUT breakdowns.

### 5. RSI edge cases

The RSI implementation in `backtest_v3.py` does not explicitly handle zero average loss / zero average gain. The calculation should define:
- gain > 0 and loss = 0: RSI = 100;
- gain = 0 and loss > 0: RSI = 0;
- gain = 0 and loss = 0: RSI = 50.

It must also reset at every continuous-segment boundary.

## Existing screening evidence from `main` (2026-11-06)

The latest report used 486,488 M1 candles from 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC, with 67 gaps and 68 continuous segments. It used a chronological 70/30 split, entry at the next candle open, settlement at the next candle close, and a fixed +0.92 / -1 / 0 payoff model.

Across 24 complete strategy/timeframe combinations (six combinations on M1, M2, M3 and M5), none had positive aggregate holdout P&L. The best aggregate holdout row was M2 Ichimoku: 2,321 trades, 51.00% win rate excluding draws, and -45.84 units.

A directional research lead was M5 Bollinger re-entry + Williams %R + ADX, PUT only:
- train: 909 trades, 54.83% win rate, +46.96 units;
- holdout: 376 trades, 53.83% win rate, +12.24 units, max drawdown 13.96 units.

This is not sufficient evidence to approve the setup:
- at a 92% payout, break-even win rate is 52.08%;
- the observed 53.83% is only about 0.68 standard errors above break-even if all 376 trades are decisive;
- an approximate 95% Wilson interval is 48.8%–58.8%, which includes break-even (and would be wider if there were draws);
- the reported holdout P&L weakened by month: June +5.08, July +12.08, August -1.12, September -0.28, October -0.04, November -3.48 units;
- the report itself notes that the positive result is concentrated early in the holdout.

The candidate therefore remains a research lead only. It needs a genuinely untouched forward sample and robustness checks; repeatedly tuning against this holdout would invalidate it.

## Limitations of the screening report

The report explicitly notes that it approximates binary settlement from OHLC (next open to next close), without spread, slippage, quote latency, or exact Pocket Option settlement quotes. Its 92% payout is a scenario, not per-trade observed payout data.

## Required correction sequence

1. Build one gap-aware calculation path: validate OHLC and timestamps, segment continuous data, reset indicator state per segment, and enforce warm-up.
2. Build one shared non-overlapping trade scheduler for CALL and PUT.
3. Accept a runtime payout scenario and optional per-entry payout data; calculate each trade's P&L using its own payout.
4. Add deterministic unit tests for RSI edge cases, segment resets, gap rejection, expiry indexing, payout handling, and non-overlap.
5. Re-run the existing strategy screen with the corrected engine, then use walk-forward / untouched forward validation. Do not promote any strategy based on the current holdout alone.

No strategy or live-trading setting is changed by this audit.
