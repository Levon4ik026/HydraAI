# Guest-feed collector code review — 2026-11-08

## Scope
- Reviewed the user-supplied `guest_feed_reconnect.py` (1,168 lines).
- The file compiles successfully with Python 3.13 after decoding its UTF-8 BOM.
- This is a static source review. No Pocket Option connection was opened and no live collector was run.
- No local Desktop files, CSVs, or production trading logic were changed.
- No raw guest token or user feed files were copied into this report.

## Confirmed findings

### 1. The collector has two independent OHLC write paths
- Live stream path: `updateStream` rows update an in-memory `current_candle`; the candle is written by `save_candle()` only after a tick from a later minute arrives.
- Server-history path: `updateHistoryNewFast` and `loadHistoryPeriodFast` call `merge_history_candles()`, which accepts server OHLC rows and rewrites the CSV.
- `parse_ohlc()` validates positive values and OHLC geometry, but does not reject or tag flat candles.
- Therefore the 605-row flat tail could have originated from the server-history merge, from the stream builder receiving only one unchanged price per minute, or a mixture. The CSV does not preserve source provenance, so the exact origin cannot be determined from this script plus OHLC file alone.

### 2. Server-history merge overwrites existing rows without source provenance
- For every valid server candle, `merged[minute] = values` replaces an existing CSV row for that minute.
- The file is then truncated and rewritten from the merged dictionary.
- The merge records counts but does not retain whether a final row came from live stream or server history, nor whether the server row was flat.
- This makes retrospective attribution impossible and can replace a previously moving local candle with a flat server candle.

### 3. Timestamp-offset handling is inconsistent between load-history response paths
- The text Socket.IO `42...` handler for `loadHistoryPeriodFast` calls `merge_history_candles()` without an explicit offset, so it uses the default `PO_TIME_OFFSET_SECONDS = 7200`.
- The binary `loadHistoryPeriodFast` handler explicitly passes `timestamp_offset=0`.
- The same named history event therefore receives different timestamp conversion depending on transport/packet path.
- The correct offset for each server payload format must be established from captured raw payloads before changing either value. Do not blindly unify the offsets.

### 4. Connection logging is coarse
- The log records only CONNECTING and CONNECTION_LOST. It does not log successful handshake, auth, subscription, first stream tick, last stream tick, history merge counts by event source, or session duration on termination.
- Consequently the connection log cannot show whether a successful socket session was actually receiving EURUSD stream ticks before the connection closed.

### 5. Reconnection state is partly retained, but feed continuity is not proven
- `current_candle` is kept in memory across reconnect attempts.
- Server history can clear the pending candle if its timestamp is covered by the latest merged history.
- The script warns about minute gaps but does not persist a source-aware quality state or mark the exact reason for each gap.
- The `recovering` argument is passed to `run_session` but is not used inside that function.

### 6. Last open candle is intentionally discarded on Ctrl+C
- The top-level KeyboardInterrupt handler prints: “Open candle was not saved.”
- This does not explain the flat historical tail, but it means the final in-progress minute may be absent after a normal stop.

## Plausible explanation for the 605 flat rows — not proven
- The supplied data audit found 605 consecutive flat rows at 1.11394 beginning 2026-11-07 10:15 UTC, on a Saturday.
- The script accepts flat OHLC from server history and unconditionally merges it.
- A market-closed/stale server-history response is a plausible source, but the current collector does not log event-source provenance for individual CSV rows. It is not proven that the flat rows came from `updateHistoryNewFast` rather than `updateStream`.

## Recommended next implementation (isolated research copy only)
1. Add explicit per-row provenance metadata to a sidecar diagnostic log (not the production candle CSV schema): source event, raw timestamp, corrected UTC timestamp, OHLC, receive time, and whether a history merge added/replaced the row.
2. Add counters for flat rows separately for live-stream aggregation and each history event.
3. Make timestamp conversion explicit per event type and reject unknown timestamp conventions; preserve raw server timestamps in diagnostics.
4. Add connection lifecycle records: handshake success, auth success, subscription sent, first EURUSD stream tick, last tick, disconnect reason, session duration.
5. Add a no-silent-overwrite policy: if server history replaces a non-flat local row with a flat row (or vice versa), log the conflict and preserve both versions in diagnostics.
6. Keep flat rows and market-closure periods out of research-quality M1/M5 sets unless independently corroborated. Do not synthesize or forward-fill prices.
7. Add deterministic offline tests for timestamp-offset paths, merge conflict handling, flat-candle provenance, and reconnect continuity before any new live run.

## Disposition
- This review does not authorize changing `C:\HydraAI_Desktop` or replacing the user's collector.
- No production/stabilization or main branch changes were made.
- Research-only recommendations are recorded here for a controlled implementation and test cycle.
