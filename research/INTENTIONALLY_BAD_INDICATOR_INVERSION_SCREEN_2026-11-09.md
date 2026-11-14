# Intentionally Bad Indicator Inversion — First Screen (2026-11-09)

## Status

Exploratory historical screen only. No production changes, no trading instructions, no live execution validation.

Repository branch: `hydra/research-validation`  
Dataset: `eurusd_research_clean.csv`  
Rows: 486,488 one-minute candles; 68 uninterrupted segments; 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC.  
SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`

## Hypothesis

A deliberately misinterpreted momentum-style indicator may be systematically wrong at exhaustion points. The first candidate is an RSI extreme *momentum-follow* rule:

- RSI(14) crosses up through 70 -> CALL.
- RSI(14) crosses down through 30 -> PUT.

This is intentionally the wrong interpretation for a mean-reversion use of RSI. Its inversion is:

- RSI crosses up through 70 -> PUT.
- RSI crosses down through 30 -> CALL.

The purpose is not to claim RSI is inherently bad. It is to test whether the deliberately adverse interpretation has stable negative predictive value and whether the exact inverse has positive expectancy.

## Method

- RSI(14), Wilder-style exponential smoothing, calculated independently within each uninterrupted data segment.
- Signals occur only on the threshold-crossing candle close (not on every candle RSI remains extreme).
- Entry is next M1 candle open; outcome is measured at the close after 1, 3, 5, 10, 15, or 20 minutes.
- One-position-per-rule schedule: after an entry signal, the next signal is eligible only once the previous expiry candle has closed.
- CALL wins if expiry close > entry open; PUT wins if expiry close < entry open; equal price is a draw.
- Fixed hypothetical payout: +0.92 units per win, -1 per loss, 0 draw. Break-even decisive win rate = 52.0833%.
- Chronological splits by signal timestamp: TRAIN before 2026-05-08; VALIDATION 2026-05-08 through 2026-08-05; TEST from 2026-08-06. Signals whose expiry would cross a data-segment gap are excluded.
- No thresholds or parameters were optimized on VALIDATION/TEST.

## Main candidate: RSI momentum-follow, then exact inversion

The original momentum-follow interpretation is negative in all splits and at every tested horizon shown below. The inverse is above the 92%-payout break-even rate in all three splits at every horizon, but its margin is small in several cells.

### Inverted results (CALL/PUT reversed)

| Expiry | Split | Trades | Inverse wins | Inverse losses | Draws | Inverse decisive WR | Net units |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1m | TRAIN | 8,115 | 4,037 | 3,605 | 473 | 52.83% | +109.04 |
| 1m | VALIDATION | 2,281 | 1,137 | 1,016 | 128 | 52.81% | +30.04 |
| 1m | TEST | 2,359 | 1,164 | 1,060 | 135 | 52.34% | +10.88 |
| 3m | TRAIN | 7,676 | 3,935 | 3,486 | 255 | 53.03% | +134.20 |
| 3m | VALIDATION | 2,162 | 1,112 | 967 | 83 | 53.49% | +56.04 |
| 3m | TEST | 2,231 | 1,127 | 1,017 | 87 | 52.57% | +19.84 |
| 5m | TRAIN | 6,947 | 3,655 | 3,136 | 156 | 53.82% | +226.60 |
| 5m | VALIDATION | 1,941 | 997 | 890 | 54 | 52.84% | +27.24 |
| 5m | TEST | 1,992 | 1,010 | 925 | 57 | 52.20% | +4.20 |
| 10m | TRAIN | 5,834 | 3,078 | 2,637 | 119 | 53.86% | +194.76 |
| 10m | VALIDATION | 1,627 | 897 | 693 | 37 | 56.42% | +132.24 |
| 10m | TEST | 1,704 | 892 | 782 | 30 | 53.29% | +38.64 |
| 15m | TRAIN | 5,197 | 2,753 | 2,371 | 73 | 53.73% | +161.76 |
| 15m | VALIDATION | 1,473 | 765 | 684 | 24 | 52.80% | +19.80 |
| 15m | TEST | 1,508 | 800 | 674 | 34 | 54.27% | +62.00 |
| 20m | TRAIN | 4,739 | 2,547 | 2,128 | 64 | 54.48% | +215.24 |
| 20m | VALIDATION | 1,351 | 727 | 606 | 18 | 54.54% | +62.84 |
| 20m | TEST | 1,391 | 738 | 637 | 16 | 53.67% | +41.96 |

### Monthly stability of inverse (TEST only)

| Expiry | 2026-08 WR / net | 2026-09 WR / net | 2026-10 WR / net | 2026-11 partial WR / net |
|---:|---:|---:|---:|---:|
| 10m | 58.61% / +48.76u | 52.36% / +2.96u | 51.62% / -5.52u | 48.72% / -7.56u |
| 15m | 61.60% / +63.80u | 52.69% / +5.60u | 51.30% / -8.16u | 52.48% / +0.76u |
| 20m | 60.24% / +52.00u | 53.13% / +8.96u | 50.30% / -17.24u | 51.09% / -1.76u |

The apparent aggregate TEST advantage is heavily front-loaded in August 2026. September is only modestly above break-even, October is negative at 10/15/20m, and November is a small partial month. This is a material regime-stability warning.

## Other intentionally adverse candidates: 15-minute expiry, inverse results

| Original rule | Split | Trades | Inverse decisive WR | Inverse net units |
|---|---|---:|---:|---:|
| EMA8/EMA21 crossover follow | TRAIN | 8,496 | 50.93% | -184.96 |
| EMA8/EMA21 crossover follow | VALIDATION | 2,623 | 50.87% | -59.88 |
| EMA8/EMA21 crossover follow | TEST | 2,692 | 49.62% | -124.56 |
| RSI extreme momentum-follow | TRAIN | 5,197 | 53.73% | +161.76 |
| RSI extreme momentum-follow | VALIDATION | 1,473 | 52.80% | +19.80 |
| RSI extreme momentum-follow | TEST | 1,508 | 54.27% | +62.00 |
| 20-bar breakout follow | TRAIN | 11,655 | 52.45% | +79.92 |
| 20-bar breakout follow | VALIDATION | 3,484 | 51.51% | -37.80 |
| 20-bar breakout follow | TEST | 3,576 | 52.56% | +32.24 |
| Three-candle momentum follow | TRAIN | 14,264 | 51.27% | -218.88 |
| Three-candle momentum follow | VALIDATION | 4,289 | 51.36% | -58.64 |
| Three-candle momentum follow | TEST | 4,488 | 50.82% | -106.80 |
| Five-minute impulse follow (±0.03%) | TRAIN | 8,117 | 53.00% | +142.12 |
| Five-minute impulse follow (±0.03%) | VALIDATION | 1,891 | 52.55% | +16.68 |
| Five-minute impulse follow (±0.03%) | TEST | 1,782 | 51.64% | -14.88 |

Important: the inverse of the EMA and three-candle rules does not beat break-even. The breakout inverse is mixed. RSI is the only candidate in this first screen that clears the break-even rate in all three splits across all tested horizons, but the edge is small in TEST at 1/3/5 minutes and monthly results expose substantial regime dependence.

## Interpretation

1. **There is a real candidate worth a second, stricter audit:** the inverse of the RSI extreme momentum-follow interpretation.
2. **This is not proof of a deployable edge.** The strongest 15m TEST result is +62.00 hypothetical units on 1,508 signals, but the monthly breakdown shows that most of the gain came in August. October weakened materially.
3. The 92% payout is hypothetical and held fixed. Actual Pocket Option payout changes by instrument/time; platform quote differences, spread, latency, and settlement rules are not modeled.
4. The data are historical Dukascopy BID candles, not Pocket Option executable quotes. No slippage/quote-side or execution model is included.
5. The one-position schedule reduces overlapping trades within each rule, but sequential outcomes remain time-dependent. The displayed win rates are descriptive, not independent Bernoulli trials.
6. Five candidate families and six expiries were screened. No multiple-comparison correction or untouched final holdout has yet been applied. Parameter and family selection bias remain.
7. The partial November segment is not a full month.

## Next validation gate (before any use in HydraAI)

- Freeze RSI(14), 70/30 crossing rules and a single expiry chosen *before* a fresh evaluation; do not pick the best expiry from this same TEST.
- Re-run on an untouched later period when available, plus date-block bootstrap / block permutation rather than naive independent-trade confidence intervals.
- Repeat with alternative quote data or Pocket Option demo capture, and include actual payout per signal.
- Audit signal timing at minute granularity, data gaps, event clustering, and sensitivity to one-minute entry delay.
- Do not add this to the production dashboard or enable any automated execution. The current research branch only is affected.

## Reproducibility note

This report was generated from the cleaned CSV identified by SHA-256 above. Signal timestamps are candle closes; entry is the next candle open. The results are a first-pass screening audit, not a final statistical validation.
