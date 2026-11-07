# Frozen PUT candidate — prospective validation protocol (2026-11-07)

## Status

The candidate is now frozen as a research-only rule. No Desktop, production strategy, or CALL logic was changed. The historical sample has already been repeatedly inspected; it is not a fresh validation set.

Implementation: `research/frozen_put_candidate.py`

## Locked rule (do not tune during forward test)

Evaluate after each completed UTC-aligned M5 candle:

1. BB(20), 2 population standard deviations: previous close > previous upper band and current close < current upper band.
2. Williams %R(14): previous value >= -20 and current value < -20.
3. Wilder ADX(14): 15 <= ADX < 25.
4. Prior 3-bar M5 momentum: current signal candle close minus close three M5 candles earlier > 0.
5. Wilder ATR(14) / current signal candle close >= **0.0003596314**.

Execution simulation:
- Entry: immediately following complete M5 candle open.
- Expiry: that entry candle close (5 minutes after entry).
- Outcome: PUT wins if entry candle close < entry candle open; loss if greater; draw if equal within 1e-12.
- Payout fixed at +0.92 / -1 / 0.
- No trade across missing M5 buckets or segment boundaries.
- Evaluate every signal in chronological order. A new signal at the prior trade's expiry candle close may enter the next candle.
- Do not use OTC symbols.

## Prospective boundary and source

The frozen M1 research source ends at 2026-11-05 16:08 UTC. The one-shot replay script retains **2026-11-05 16:10 UTC** as its historical comparison boundary; that date is not the start of the new prospective experiment. The continuous monitor described below creates a fresh forward boundary at its first launch (next UTC M5 boundary) and persists it. Only genuinely new candles after that launch boundary qualify.

## Running

From the repository root, after appending new non-OTC EURUSD M1 OHLC rows to a CSV with either `datetime_utc` or `datetime` plus `open,high,low,close`:

```powershell
python research/frozen_put_candidate.py --data .\observer_data\eurusd_guest_candles.csv
```

The script writes `research/frozen_put_candidate_trades.csv` (or the path passed to `--out`) and reports historical versus forward outcomes separately. Do not overwrite the frozen script or ledger between checkpoints; archive each ledger snapshot with its data-source hash.

## Precommitted reporting checkpoints

- First descriptive checkpoint: 50 forward decisive trades.
- First meaningful review: 100 forward decisive trades and at least 4 calendar weeks.
- No parameter changes or threshold search on the forward period.
- Report all eligible trades, not only wins; include W/L/draw, net units at 92%, Wilson 95% interval, max drawdown, weekly/monthly dispersion, missing-data exclusions and data hash.
- A candidate is not accepted solely because point WR exceeds 52.0833%. The confidence interval, chronological stability, execution delay/spread sensitivity, and sufficient independent time coverage must also be considered.
- If fewer than 100 decisive trades accumulate, report the result as preliminary. Do not extrapolate or promote to production.

## Known limitations

- The exact source code and training timestamps for the legacy 376-trade PUT log remain unrecovered.
- The earlier 81-trade regime result came from an exploratory pandas/Wilder-style reconstruction. The frozen runner uses the repository's seeded indicator implementation and an explicitly fixed ATR/close threshold; its historical replay may differ. This is intentional: the frozen runner defines the prospective rule from this point onward.
- The forward sample is not yet available in the committed historical source. The script can only score it after genuinely new candles are appended.
- No live quote execution, spread, payout changes, or network latency are simulated. This remains a demo/research-only signal study.

## Decision

Keep the candidate outside production. Keep CALL unchanged. Start forward collection with the exact frozen rule, then review at the precommitted checkpoints without retuning.


## Continuous monitor (added after protocol freeze)

Use `research/watch_frozen_put_candidate.py` alongside the existing guest-feed collector. It watches the collector's M1 CSV; it does not connect to Pocket Option itself and does not alter the collector.

First launch automatically freezes the forward boundary at the next UTC M5 boundary and stores it in `observer_data/hydra_put_forward_state.json`. On restart, the same boundary is reused. The monitor refuses a different `--forward-start` when a state file already exists.

Example from the repository root (PowerShell):

```powershell
python research/watch_frozen_put_candidate.py --data "C:\HydraAI_Desktop\observer_data\eurusd_guest_candles.csv"
```

Run this in a second PowerShell window while the existing EUR/USD guest-feed collector is running. The monitor:
- polls the CSV every 15 seconds;
- requires a fresh latest M1 timestamp (maximum age 180 seconds);
- only records a trade after its M5 expiry candle has completed;
- appends settled trades to `observer_data/hydra_put_forward_trades.csv`;
- persists the frozen start, data hash, latest timestamp, and cumulative W/L/draw counts in `observer_data/hydra_put_forward_state.json`;
- never sends orders or calls a trading endpoint.

Do not delete the state or ledger during the experiment. The ledger and state are local runtime outputs and are not committed to Git. If the collector CSV is located elsewhere, change only the `--data` path. The first launch time is the actual prospective start; old records already present in the CSV are excluded by the automatically frozen boundary.

The monitor is deliberately a separate process rather than a modification to the Desktop GUI or collector. This keeps the research experiment isolated and lets collection continue if the UI is closed.


Windows launcher: from the repository folder, double-click `start_put_forward_monitor.bat`. It expects the guest-feed CSV at `C:\\HydraAI_Desktop\\observer_data\\eurusd_guest_candles.csv` and opens the monitor in the current console. Keep the guest-feed collector running in its own window.
