# HYDRA — prospective Pocket Option DEMO validation protocol

Status: preregistered protocol; research-only. Created 2026-11-08.
Branch: hydra/research-validation.
This document freezes the next prospective test. It does not authorize production integration or automated trading.

## Objective

Test whether the previously identified New York PUT candidate retains an edge on the actual Pocket Option DEMO EURUSD quote stream, without retuning it on the incoming data.

## Frozen candidate (do not alter)

- Instrument: EURUSD only; exclude OTC.
- Signal timeframe: M5, constructed only from completed M1 candles.
- Signal family: existing frozen BB(20, 2) re-entry + Williams %R(14) cross + ADX(14) PUT trigger.
- Direction: PUT only.
- New York local clock: 08:00 through 12:59 inclusive, using the IANA timezone America/New_York (DST-aware).
- State filters at the completed signal candle: ADX >= 25; +DI > -DI; close[i] > close[i-12].
- Entry: next M5 candle open after signal close.
- Expiry: 20 minutes, measured to the close four M5 candles after entry.
- Position policy: one position at a time; suppress any new signal whose entry would overlap the active 20-minute position. If timestamps or candle continuity do not support an unambiguous entry/expiry, skip and log the reason.
- Payout: record the actual displayed Pocket Option payout for each prospective trade. Primary reporting uses realized per-trade payout; also show sensitivity at 85%, 90%, and 92%. Never silently assume 92% if actual payout differs.
- Outcomes: WIN / LOSS / DRAW; net = actual payout on WIN, -1 unit on LOSS, 0 on DRAW.

## Data handling and integrity

1. Preserve the raw uploaded/exported CSV unchanged and calculate a SHA-256 checksum before processing.
2. Required columns: datetime_utc, open, high, low, close. Preserve any additional original fields.
3. Parse timestamps as UTC; verify monotonic ordering, duplicates, malformed rows, OHLC consistency, missing minutes, and future timestamps.
4. Do not interpolate missing OHLC candles. Break the data into continuous segments; indicators must not cross segment boundaries.
5. Construct M5 bars only from five valid consecutive M1 candles aligned to UTC five-minute boundaries. A partial M5 bar is never a signal candle.
6. Exclude the currently forming candle and all signals lacking the full 20-minute forward path.
7. Convert each completed signal timestamp to America/New_York only for the session filter. Do not use a fixed UTC offset.
8. Report source, date coverage, row counts, gaps, duplicate count, segment count, payout availability, and timestamp alignment before computing performance.
9. Keep this prospective dataset separate from Dukascopy research data. Never mix it into threshold selection, feature selection, or model training.

## Primary endpoint and reporting

- Primary endpoint: net units per eligible non-overlapping trade at the actual recorded payout.
- Also report W/L/D, decisive win rate (W / (W + L)), payout break-even rate for the observed payout, profit factor, cumulative net, maximum drawdown, maximum loss streak, active trading days, and trades per 20 trading days.
- Report all results chronologically by month and by the full accumulated sample.
- Report signal counts rejected for overlap, incomplete path, gaps, invalid payout, or bad data.
- Show both candidate-only results and signal frequency. Do not extrapolate daily trade counts from unrelated strategies.
- No interim threshold tuning, feature selection, or model fitting on this dataset.

## Sample-size and stopping rule

- Accumulate 333 decisive outcomes (WIN or LOSS) before making the primary efficacy assessment. DRAWs do not count toward 333 but remain in all operational counts and net results.
- Do not stop early because results look good or bad. Stop early only for data-integrity failure, a changed feed/schema, or a safety/operational issue; document the reason and do not call it an efficacy result.
- At 333 decisive outcomes, report the full result and uncertainty intervals, but do not claim guaranteed future profitability. Any subsequent change to the candidate requires a new prospective version and a new untouched sample.

## Decision gates

A candidate is not eligible for integration unless all are true:
1. The dataset is genuine Pocket Option DEMO EURUSD (non-OTC) data with auditable provenance and acceptable continuity.
2. The frozen rule was applied exactly as written, with no look-ahead and no tuning.
3. Net expectancy is positive using the actual recorded payouts.
4. The uncertainty analysis accounts for day-level clustering; report a trading-day block bootstrap interval for net units and win rate.
5. The result is not carried by one isolated month; provide monthly and leave-one-month-out diagnostics.
6. The observed trade frequency is acceptable for the intended workflow and is stated honestly.
7. Independent review finds no timestamp, overlap, payout, or outcome-label bug.

Failure of any gate means remain research-only. A positive backtest alone is not sufficient.

## Explicit non-goals

- No automatic order placement.
- No OTC instruments.
- No change to the Desktop math core or stabilization branch.
- No use of the prospective sample to optimize parameters.
- No claim that Dukascopy BID outcomes equal Pocket Option quotes or execution.
