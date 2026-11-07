# HydraAI research backtest engine — specification

## Scope

research/backtest_engine.py is an isolated, standard-library-only scoring engine. It accepts already-computed signal indices; it does not calculate indicators, select strategy parameters, connect to Pocket Option, or place orders. It must not be imported by the desktop application.

## Candle and execution convention

- Candle timestamps are timezone-aware UTC candle open times.
- Signal at index N is known only after candle N closes.
- Entry is the next candle (N+1) open.
- H-minute settlement is the close of candle N+H (for M1 data).
- Every timestamp from signal candle through settlement must be exactly one configured interval apart. A trade crossing a gap is skipped.
- Duplicate or out-of-order timestamps are rejected; source rows are never silently sorted or deduplicated by the engine.
- The caller is responsible for passing closed candles only and computing signals without look-ahead.

## Payout and outcomes

- Default scenario payout: 92%.
- WIN: +0.92 units at 92% payout.
- LOSS: -1.00 unit.
- DRAW: 0 units.
- Payout may be supplied as a fixed scenario value or as a mapping from signal index to payout. Missing mapping entries use 92%.
- Win rate is calculated over decisive trades only (wins + losses); draws are separately counted.
- For variable payouts, a single break-even win-rate figure is deliberately omitted.

## Horizons and scheduling

M1 horizons 1, 2, 3 and 5 minutes are the supported baseline set. The generic engine accepts any positive horizon that is an exact multiple of the candle interval. Non-overlapping mode is the default; after a trade settles, signals during that trade are ignored. An overlapping mode is available for diagnostic comparisons and must be labelled clearly.

## Chronological evaluation

- chronological_partitions returns half-open index ranges for Train / Validation / Holdout (default 60/20/20).
- walk_forward_windows creates expanding training windows and subsequent validation windows.
- trades_in_window keeps signals in a half-open time window only when settlement also completes before the window ends. This prevents a trade opened in one partition from being scored using prices from the next partition.
- Indicator warm-up and parameter selection remain the caller's responsibility. For a strict experiment, calculate indicators causally on the full chronological series, select parameters on Train/Validation only, freeze them, then score Holdout once.

## Metrics

summarize_trades reports trade count, wins/losses/draws, decisive win rate, net units, expectancy per trade, maximum peak-to-trough drawdown, maximum consecutive losses, mean payout, and fixed-payout break-even win rate.

## Non-goals and limitations

This engine does not model broker quote latency, spread, rejected orders, payout changes during the holding period, intrabar price paths, or execution slippage. The OHLC entry/settlement convention is a reproducible research approximation, not proof of real fill quality. A positive historical result is not production approval. Independent out-of-sample validation and prospective testing remain mandatory.

## Tests

Run:

    python -m unittest discover -s research/tests -v

Tests cover next-candle entry, 92% payoff arithmetic, variable payout, gap rejection, duplicate timestamp rejection, non-overlap, draws, chronological splits, walk-forward windows, and partition-boundary settlement.
