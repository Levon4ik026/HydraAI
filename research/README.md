# HydraAI Research — Module 1: Data foundation

This directory is an isolated research workspace. It does not modify the live application or execute trades.

## Current deliverable

`data_audit.py` performs a structural audit of an OHLC candle CSV using only the Python standard library.

It records:
- source file SHA-256, byte size and filename;
- parsed row count, unique timestamps and duplicate timestamp groups;
- invalid OHLC rows and flat candles;
- gaps relative to the configured candle interval;
- source ordering, UTC range, weekend-row count and naive timestamp count;
- row-level parse/validation issues.

The tool never repairs, reorders, deduplicates or silently removes source rows. It sorts a separate in-memory view only to measure time gaps. Naive timestamps are interpreted as UTC and explicitly counted for review. Weekend rows are reported, not automatically discarded.

## Run

From the repository root:

```powershell
python research/data_audit.py "C:\path\to\eurusd_history_extended.csv"
```

Optional outputs:

```powershell
python research/data_audit.py "C:\path\to\candles.csv" --interval-seconds 60 --report research\reports\candles.audit.json --issues-csv research\reports\candles.issues.csv
```

Exit codes:
- `0`: no parse or OHLC validation issues;
- `1`: audit completed and found row-level issues;
- `2`: audit could not run (missing file, missing required columns, unreadable CSV, etc.).

## Accepted columns

Timestamp aliases: `timestamp`, `time`, `datetime`, `date`, `time_utc`, `open_time`.

OHLC aliases: full names or `o/h/l/c`. Optional volume aliases are recognized for future use but are not required by this audit.

Timestamps may be ISO-8601 (with or without timezone), Unix seconds or Unix milliseconds. Timezone-naive timestamps are assumed UTC and counted in the report.

## Validation

Run unit tests from the repository root:

```powershell
python -m unittest discover -s research/tests -v
```

## Important limitations

A structurally valid CSV is not proof of quote parity with Pocket Option, completeness of the market feed, correct candle boundaries, or realistic trade execution. Those checks are separate research tasks. Do not use the preliminary audit alone to approve a strategy.
