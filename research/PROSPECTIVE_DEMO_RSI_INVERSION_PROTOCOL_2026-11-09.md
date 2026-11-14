# Prospective DEMO validation protocol — frozen RSI inverse (2026-11-09)

## Purpose and status

Research-only protocol for testing the selected inverse RSI rule on Pocket Option DEMO. It does not authorize or implement trade execution. No production HydraAI code is changed.

Historical evidence is insufficient to claim an edge: the clean Dukascopy BID TEST had 1,510 observations, 803/673/34 inverse W/L/D, 54.40% decisive win rate and +65.76 hypothetical units at a constant 92% payout. The gain was concentrated in August 2026; October was negative, and 7/14/21-day block-bootstrap net intervals included zero. This protocol freezes the candidate and moves to prospective platform observation.

## Frozen rule — do not tune during collection

- Instrument: standard EUR/USD only; OTC prohibited.
- Account: Pocket Option DEMO only.
- Indicator: RSI(14), Wilder smoothing, computed from completed 1-minute candles.
- Raw trigger A: RSI crosses upward through 70 (baseline CALL); inverse candidate direction is PUT.
- Raw trigger B: RSI crosses downward through 30 (baseline PUT); inverse candidate direction is CALL.
- Crossing: previous completed RSI <= 70 and current > 70; or previous >= 30 and current < 30.
- Signal timestamp: close time of the completed candle confirming the crossing.
- Entry reference: first platform quote observable after signal confirmation / next minute boundary. Record actual timestamp and quote; do not silently substitute a candle open.
- Expiry: 15 minutes after recorded entry timestamp, using actual platform settlement/result as primary outcome. Record expiry quote and result.
- One accepted signal locks out further accepted signals for 15 minutes. Preserve every raw crossing, including lockout rejects.
- No thresholds, RSI period, expiry, session filters, or lockout rules may change after collection begins. Later variants require a separately preregistered experiment.

## Capture rules

1. Record every raw crossing, including those rejected by lockout, stale/missing feed, platform unavailable, or inability to observe quote.
2. Capture Pocket Option DEMO platform quotes and displayed payout at decision and entry. If both quote sides are exposed, record both; otherwise label the quote source exactly as displayed.
3. Record candidate direction, hypothetical outcome, actual displayed payout, and whether a DEMO trade was manually placed. Research result must not depend on whether a trade was placed.
4. For each accepted signal, capture platform settlement/result at expiry. If unavailable, mark UNKNOWN; do not infer a win from external candle data.
5. Record local and UTC timestamps, timezone/UTC offset, and clock source. Keep raw logs immutable; corrections go into a separate note.
6. Never automate clicking, order placement, account interaction, or trade execution. Passive/manual observation only.

## CSV schema

One row per raw crossing. UTF-8 CSV; ISO-8601 timestamps with explicit UTC offset, preferably Z. Empty fields mean unavailable; status columns must distinguish missingness.

| Column | Meaning |
|---|---|
| event_id | Stable unique ID |
| instrument | EURUSD; explicitly record OTC=false |
| signal_time_utc | Completed candle close confirming crossing |
| signal_time_local | Local timestamp as displayed/observed |
| rsi_prev | RSI on previous completed M1 candle |
| rsi_current | RSI on crossing candle |
| baseline_side | CALL for cross-up-70; PUT for cross-down-30 |
| candidate_side | Inverse side: PUT or CALL |
| lockout_status | ACCEPTED / REJECTED_LOCKOUT |
| data_status | FRESH / STALE / GAP / UNKNOWN |
| reject_reason | LOCKOUT / STALE_FEED / GAP / PLATFORM_UNAVAILABLE / OTHER / blank |
| platform_quote_decision | Platform EUR/USD quote at decision |
| quote_source_decision | Exact UI/source label and quote side if known |
| payout_decision_pct | Displayed payout at decision, numeric percent |
| decision_observed_utc | Timestamp quote/payout observed |
| platform_quote_entry | Platform quote at entry reference |
| quote_source_entry | Exact UI/source label and quote side if known |
| payout_entry_pct | Displayed payout at entry, numeric percent |
| entry_observed_utc | Timestamp entry quote observed |
| planned_expiry_utc | Entry timestamp + 15 minutes |
| platform_quote_expiry | Platform quote observed at expiry |
| expiry_observed_utc | Timestamp expiry quote observed |
| platform_result | WIN / LOSS / DRAW / UNKNOWN / NOT_PLACED |
| displayed_payout_settlement_pct | Payout applicable to event, if confirmed |
| manual_demo_trade | YES / NO |
| notes | UI anomalies, latency, disconnection, ambiguity |

## Evaluation plan (predeclared)

- Keep a chronological append-only event log. Do not inspect and tune thresholds during collection.
- Report raw crossings, accepted signals, rejects, missing observations, unknown outcomes, and manually placed DEMO trades separately.
- Primary performance set: accepted signals with observed platform result and known applicable payout. Also publish conservative sensitivity treating UNKNOWN outcomes as losses; never hide missingness.
- Per-event net units: WIN = payout fraction; LOSS = -1; DRAW = 0. Use payout recorded for that event, not a fixed 92%.
- Report decisive win rate, net units, profit factor, payout distribution, missing/unknown rate, median and 95th-percentile decision-to-entry delay, and results by calendar week. Do not treat clustered observations as independent.
- First diagnostic review gate: 200 accepted signals AND at least 4 complete calendar weeks, whichever takes longer. This is not proof of an edge. Continue to 500 accepted signals and at least 8 complete weeks before stronger review.
- No strategy changes based on interim results. If the frozen rule fails, stop and document failure; do not keep changing parameters on the same prospective sample.

## Data integrity checklist

- Keep original raw Pocket Option observation/export files.
- Store collector version, commit, machine clock/timezone, instrument label, account mode DEMO, and collection start/end.
- Deduplicate only by event_id; do not overwrite raw events.
- Reconcile candle-derived signal time against actual platform observation time; report delays rather than backdating.
- Distinguish missing quotes, stale feed, lockout rejects, skipped observations, unplaced hypothetical trades, and platform settlement outcomes.

## Explicit limitations

The historical study used external EUR/USD BID candles and a hypothetical constant payout. It did not reproduce Pocket Option executable quotes, quote-side conventions, changing payout, platform settlement, or observation latency. This prospective DEMO protocol is designed to measure those differences; it does not guarantee DEMO results transfer to a live account.

## Start condition

Do not claim collection has started until a real DEMO observation session has produced and verified the first append-only event row. The existing guest candle collector is known to store OHLC candles; its ability to capture displayed payout, platform quote sides, and settlement has not yet been verified. Do not imply those fields are already collected.
