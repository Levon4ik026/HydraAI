# HydraAI Research — isolated research workspace

This directory contains research-only data-quality and backtesting tools. It does not modify the live application or execute trades.

## Data foundation

research/data_audit.py audits OHLC CSV structure using only the Python standard library. It reports source SHA-256, row counts, duplicate timestamps, invalid OHLC rows, flat candles, gaps, ordering, UTC range and parse issues. It never repairs, reorders, deduplicates or silently removes source rows.

Run:

    python research/data_audit.py "C:\path\to\eurusd_history_extended.csv"
    python -m unittest discover -s research/tests -v

## Backtest engine

research/backtest_engine.py scores caller-supplied CALL/PUT signals on closed candles. It uses next-candle-open entry, elapsed-time settlement, gap-safe trade rejection, 92% default payout (+0.92 / -1 / 0), optional per-trade payout, non-overlapping scheduling, chronological partitions, walk-forward window construction and risk metrics.

Read research/BACKTEST_ENGINE_SPEC.md before using it. The engine does not calculate indicators, choose strategy parameters, access a broker, or place trades. It is not connected to the desktop app.

## Important limitations

A structurally valid CSV is not proof of quote parity with Pocket Option, complete feed coverage, correct broker candle boundaries, or realistic execution. Historical backtests are research evidence only; independent out-of-sample and prospective validation are required.
