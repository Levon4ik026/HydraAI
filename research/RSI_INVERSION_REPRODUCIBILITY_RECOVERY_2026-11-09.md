# RSI inversion reproducibility recovery — 2026-11-09

## Scope and safety

This is a reproducibility recovery, not a new strategy search. Work is confined to `hydra/research-validation`. No production HydraAI files, main branch, stabilization branch, or local Windows files were changed. No automatic execution is introduced.

Dataset: `eurusd_research_clean.csv`, 486,488 M1 EUR/USD BID candles, 68 continuity segments, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC. SHA-256:
`5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.

## 1. Recovery of the historical generator

I inspected the full `research/` directory on `hydra/research-validation` and the RSI/inversion reports and scripts present there. The branch contains reports for the pre-entry candle screen, RSI inversion, paired complement checks, and the simple inversion experiment. It does **not** contain the original source script that generated the pre-entry feature report or its exact trade ledger.

The available `inverse_indicator_experiment.py` is a separate broad screen (EMA/MOM/RSI/BB rules at 1/3/5-minute horizons); it is not the missing pre-entry RSI feature generator. The report itself explicitly notes a baseline event discrepancy (5,197/1,473/1,508 in earlier work versus 5,199/1,473/1,510 in its own cohort). Thus exact historical recovery cannot honestly be claimed from the current repository.

## 2. Candidate B — canonical independent reproduction

Frozen definition:
- RSI(14) crosses from at-or-below 70 to above 70 on the completed signal M1 candle.
- Invert the original CALL to PUT.
- Signal close is 3.042–5.692 EUR/USD pips above EMA50.
- EMA50 uses recursive EMA span 50, initialized from the first close in each uninterrupted data segment.
- RSI uses Wilder smoothing, seeded by the arithmetic mean of the first 14 close-to-close gains/losses in each segment.
- Signal is known at candle close; entry is next M1 open; expiry is close of the 15th entry candle (signal index + 15).
- One active position per candidate and segment; a new signal is eligible when its signal index is at or after the previous expiry candle index.
- TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06.
- Win for PUT means expiry close < entry open; loss means expiry close > entry open; exact equality is DRAW.
- Net units are W × 0.92 − L; draws contribute zero. This is arithmetic on a fixed hypothetical payout, not an executable platform backtest.

The new canonical script reproduces the latest independent audit exactly:

| Split | Trades | W | L | D | Decisive WR | Net @92% |
|---|---:|---:|---:|---:|---:|---:|
| TRAIN | 1,122 | 606 | 496 | 20 | 54.99% | +61.52u |
| VALIDATION | 349 | 194 | 151 | 4 | 56.23% | +27.48u |
| TEST | 371 | 203 | 162 | 6 | 55.62% | +24.76u |
| TOTAL | 1,842 | 1,003 | 809 | 30 | 55.35% | +113.76u |

Independent execution of the committed script against the supplied CSV returned these exact counts and values. It also generated a row-level Candidate B ledger. The script validates the CSV SHA-256 before calculating anything.

Earlier Candidate B counts (1,035 / 317 / 335) remain unreconciled. The current script freezes one fully specified implementation; it does not retroactively prove which implementation generated the earlier counts. Candidate B remains a research lead only: the historical BID source, platform quote mismatch, payout variability, latency and settlement mechanics are not modeled; the volatility regime reversal in the previous audit remains a serious stability warning.

## 3. Candidate A — upper-wick definition is unresolved

Historical headline claimed inverted CALL when “upper wick <= 0.1 pip”, with 1,278 TRAIN / 340 VALIDATION / 312 TEST trades. That definition does not reproduce under the literal calculation:

`(high - close) / 0.0001 <= 0.1`

There are 6,487 raw RSI-cross-down-30 events, but only 23 raw events meet that literal condition before the one-position schedule. The earlier independent audit also found only 8 raw events with exact `high == close`. This cannot produce the claimed 1,278/340/312 cohort.

To avoid silently choosing a different definition, the canonical script reports four separate raw feature interpretations for the same 6,487 events:

- `(high - close) / pip <= 0.1`: 23 events.
- True geometric upper wick `(high - max(open, close)) / pip <= 0.1`: 2,899 events.
- True upper wick divided by full candle range <= 0.1: 3,825 events.
- `(high - close) / candle_range <= 0.1`: 7 events.

These are materially different features. None is asserted to be the historical generator's definition. In particular, the true geometric upper wick and the high-to-close distance are not interchangeable for bearish candles.

**Decision:** Candidate A stays withdrawn. The 60.13% TEST headline and associated P&L must not be used until the original feature-generation code or original per-trade ledger is recovered.

## 4. What is now reproducible

New canonical file:
- `research/rsi_inversion_reproducibility_audit.py`

Run:
`python research/rsi_inversion_reproducibility_audit.py --data eurusd_research_clean.csv`

The script writes `research_output/rsi_candidate_b_trade_ledger.csv` with exact signal, entry and expiry timestamps, prices, outcome, split and feature values. It does not write to production folders or execute trades.

## 5. Next research gate

1. Treat Candidate B's newly frozen generator as the only reproducible current RSI candidate; do not tune its thresholds against the already-inspected TEST.
2. Keep Candidate A withdrawn until its original code/ledger is found. If unavailable, it must be treated as an irrecoverable historical claim, not reverse-engineered by picking whichever wick definition yields a favorable result.
3. For any subsequent test, use a genuinely new chronological forward period and platform-aligned quotes where possible.
4. Do not transfer either candidate to production HydraAI or enable automated trading.
