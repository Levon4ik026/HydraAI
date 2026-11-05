# Initial source and candle audit — 2026-11-05

## Scope and provenance

The following previously uploaded Library files were recovered and inspected. The archive and CSVs are evidence for this audit only; no live application file was modified.

### Current-source archive

`HYDRA_CURRENT_SOURCE.zip`
- Size: 27,887 bytes
- SHA-256: `b6ff220b03191de059d18a59a8914861e2004abe99bdc175f49c564b2c838354`
- Root entries: `main.py` (30,610 bytes), `guest_feed_reconnect.py` (37,467 bytes), `hydra_technical_metrics.py` (9,930 bytes)
- These three sizes match the latest local file-size snapshot reported by the user on 2026-11-05.
- The archive does not include `hydra_indicators.py` or `hydra_strategy_core.py`; it is therefore not a complete project snapshot and must not be treated as one.

### Candle CSV A — `eurusd_guest_candles.csv`

- SHA-256: `efc4d1b4a99e011538fdccb106c7dd5afda9a39ecc1c868bac341086c29d22b0`
- Rows: 223; unique timestamps: 223; duplicate groups: 0
- Time range: 2026-11-04 13:19–18:29 UTC
- Invalid OHLC rows: 0; flat candles: 0
- Source order: chronological
- One-minute continuity audit: 27 gaps; largest gap 2,040 seconds (34 minutes)
- Interpretation: despite the filename, this sample is not a continuous M1 series. Do not use it as an uninterrupted minute-by-minute backtest input. The gap-crossing exclusion rule is essential.

### Candle CSV B — `eurusd_candles.csv`

- SHA-256: `771fefd1f4f0fe5e98b03ed514bf8640f76ab8fbf84e01168132bb3f88b93629`
- Rows: 73; unique timestamps: 73; duplicate groups: 0
- Time range: 2026-11-01 16:22–2026-11-02 10:30 UTC
- Invalid OHLC rows: 0; flat candles: 54
- Source order: chronological
- One-minute continuity audit: 20 gaps; largest gap 45,900 seconds (12 hours 45 minutes)
- Interpretation: this is a sparse diagnostic sample, not a valid continuous M1 research dataset.

## Initial conclusion

1. Both recovered CSVs are useful for testing parser behavior and feed diagnostics, but neither is suitable for performance claims or strategy ranking.
2. The 223-row guest-feed sample has no duplicate or invalid OHLC rows, but its 27 gaps invalidate naive continuous-horizon testing.
3. The 73-row sample is heavily sparse and contains 54 flat candles; it must not be mistaken for a representative price history.
4. The previously audited 30,048-row `eurusd_history_extended.csv` remains the historical research candidate described in the prior audit. Its original bytes were not present among the recovered files in this run, so its checksum and earlier audit figures have not been independently recomputed here.
5. Before strategy experiments, the next data task is to recover the full historical CSV and document its timestamp source, candle boundary convention, and relationship to Pocket Option quotes.

## Method note

The counts above were independently recomputed from the recovered CSV bytes with Python's CSV and datetime libraries. The committed `research/data_audit.py` is the reproducible standard-library CLI intended to become the canonical audit path; CI tests have been added, but a GitHub Actions run has not yet been independently confirmed in this report.
