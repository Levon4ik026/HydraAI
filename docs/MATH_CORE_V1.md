# Hydra gap-aware math core — research implementation v1

This is an isolated research engine. It does **not** replace the live GUI's technical metrics and does not place trades.

## Contract

- Input timestamps must include a timezone and are normalized to UTC.
- Duplicate timestamps keep the last row; candles are sorted chronologically.
- Every interval other than exactly one minute starts a new segment.
- EMA and Wilder RSI are recalculated independently in each segment. EMA is withheld until its period is reached; RSI until it has 14 price changes. RSI edge cases are explicit: 100 (gain only), 0 (loss only), 50 (flat).
- A signal is read after candle i closes; entry is candle i+1 open; horizon N settles at candle i+N close. The full interval must be continuous.
- CALL and PUT share one scheduler; trades cannot overlap.
- Payout is net profit on a winning unit stake (e.g. 0.92), -1 on a loss and 0 on a draw. payout_by_entry can override it by exact UTC entry timestamp. A scalar is a scenario assumption, not a claim about the platform's actual payout.
- Optional split bounds apply to settlement timestamps.

## Tests

From repository root: `python -m unittest discover -s tests -v`

## Limitations

Not wired into HydraAI Desktop. Not run against the large historical EUR/USD CSV because that file could not be retrieved through the current GitHub file interface. Synthetic unit tests validate mechanics only and do not demonstrate a profitable edge. Before interpreting results, verify Pocket Option's exact entry/expiry quote convention, model latency and quote differences, and use observed per-trade payout in a genuinely untouched forward test.
