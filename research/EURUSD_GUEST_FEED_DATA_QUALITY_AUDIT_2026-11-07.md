# EUR/USD guest-feed data quality audit — 2026-11-07

## Scope and safety
- Audited the two user-supplied files in-session: guest M1 candles and collector connection log.
- Raw candle and connection-log files were **not** uploaded to GitHub; this report stores aggregate diagnostics only.
- No local project files, collector, GUI, trading logic, or production branch were changed.
- No orders or automatic trading; OTC remains out of scope.
- This is a feed-quality audit, not a strategy-performance test.

## Candle file
- Rows: 1,673.
- Columns: `datetime_utc, open, high, low, close`.
- Timestamp span: 2026-11-04 13:19 UTC through 2026-11-07 20:19 UTC.
- SHA-256 of supplied file: `c000db4d530bf4b973746ef95046c98e257ce2a7ff52e92ff3c8d50b5a72c881`.
- Invalid/unparseable timestamps: 0.
- Duplicate timestamps: 0.
- Out-of-order timestamps: 0.
- Timestamps not aligned to minute boundaries: 0.
- Missing/non-numeric OHLC values: 0.
- Invalid OHLC geometry: 0.
- Non-positive prices: 0.

## Critical quality finding: flat tail
- 605 rows (36.16%) are exactly flat: open = high = low = close = 1.11394.
- This flat run begins at 2026-11-07 10:15 UTC and continues without interruption through the final row at 20:19 UTC.
- These rows are not suitable as evidence of a live-moving EUR/USD market and must be quarantined/excluded from strategy research unless independently verified against the source.
- The fact that this is a Saturday interval makes a market-closure/stale-price explanation plausible, but the CSV alone does not prove why the collector emitted these bars. Do not silently treat them as genuine tradable M1 candles.

## Continuity and usable history
- The full file contains 30 timestamp-contiguous segments, separated by 29 gaps.
- There are 3 large non-flat continuous runs:
  - 286 M1 rows: 2026-11-04 15:36–20:21 UTC.
  - 529 M1 rows: 2026-11-05 12:21–21:09 UTC.
  - 203 M1 rows: 2026-11-06 17:16–20:38 UTC.
- Remaining non-flat rows are fragmented short pieces, mostly from the early 2026-11-04 startup period.
- The three large runs contain 1,018 non-flat M1 rows in total.
- Only 200 complete, UTC-aligned M5 bars can be formed from those three large runs without crossing a gap (56 + 105 + 39).
- Gaps include expected long market-closure intervals as well as short intraday interruptions. Never fill these with synthetic candles for candidate evaluation.

## Connection log
- Rows: 615; SHA-256: `03b559ad77a36d19f1e91ca247ca607fc21b7be9d5aa82b51a506092b75d469d`.
- 136 distinct connection-attempt numbers.
- Events: 323 CONNECTING, 292 CONNECTION_LOST.
- Loss details include repeated `ConnectionClosedOK` with WebSocket close code 1005, 22 heartbeat `TimeoutError` entries, 8 DNS `gaierror` entries, and 1 `ConnectionResetError`.
- Last connection-log event: 2026-11-07 21:05:55 UTC.
- Last candle timestamp precedes that event by about 47 minutes. The collector log therefore indicates reconnect/heartbeat instability after the last candle timestamp.

## Research disposition
1. Preserve both supplied originals unchanged.
2. Quarantine the 605-row flat tail; do not feed it to indicator warm-up, backtests, forward scoring, or M5 aggregation.
3. Treat the three large non-flat runs as limited feed diagnostics only. 200 M5 bars are far too few for reliable edge estimation or meaningful confirmation of the frozen PUT candidate.
4. Keep all gaps as hard segment boundaries. Do not interpolate or forward-fill.
5. Before another prospective run, investigate why the collector continued writing identical flat OHLC rows during the Saturday closure and why connection attempts/heartbeats repeatedly failed.
6. For any later comparison, use the frozen 92% payout accounting and existing frozen strategy rules without tuning on this short sample.

## Conclusion
The files are readable and structurally valid, but the sample is not a clean continuous market dataset. The 605-row flat tail and repeated connection failures are the dominant integrity issues. The dataset is useful for diagnosing the collector; it is not suitable for a strategy validation claim.


## Frozen PUT candidate diagnostic on the three non-flat runs
- Applied the currently frozen selector exactly as specified in `research/frozen_put_candidate.py` to complete M5 bars built only from the three large non-flat runs above.
- Complete M5 segment lengths: 56, 105, and 39 bars (200 total).
- Candidate trades: 2 total, both in the 105-bar 2026-11-05 segment:
  - Signal 17:30 UTC, entry 17:35 UTC: LOSS.
  - Signal 17:50 UTC, entry 17:55 UTC: WIN.
- At 92% payout: 1 WIN / 1 LOSS, 50% decisive win rate, net -0.08 units.
- This is only a mechanical smoke test showing the selector can be applied to this feed. Two trades are not statistically informative and do not validate or invalidate the strategy. No threshold was changed.
