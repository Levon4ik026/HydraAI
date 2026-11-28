# RSI 15-minute inversion: clean rerun and date-block stress test (2026-11-09)

## Executive result

The clean dataset was recovered from the user's Library and independently checked before running the canonical matched-rule calculations.

- File: `eurusd_research_clean.csv`
- Bytes: 28,489,687
- Rows: 486,488
- Range: 2025-07-21 15:11 UTC — 2026-11-05 16:08 UTC
- Segments: 68
- SHA-256 verified: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`

The follow-up five-rule experiment was rerun against that exact file. All reported counts and outcomes reproduced exactly.

## Reproduction: all five matched 15-minute inversions

Payout is hypothetical 92%; net units = 0.92 × inverse wins − inverse losses. WR excludes draws.

| Rule | Split | N | Inverse W/L/D | WR | Net |
|---|---|---:|---:|---:|---:|
| EMA 8/21 crossover | TRAIN | 8,449 | 4,239/4,085/125 | 50.93% | -185.12 |
| EMA 8/21 crossover | VALIDATION | 2,609 | 1,304/1,259/46 | 50.88% | -59.32 |
| EMA 8/21 crossover | TEST | 2,677 | 1,299/1,320/58 | 49.60% | -124.92 |
| 20-bar breakout | TRAIN | 11,916 | 6,177/5,570/169 | 52.58% | +112.84 |
| 20-bar breakout | VALIDATION | 3,553 | 1,785/1,699/69 | 51.23% | -56.80 |
| 20-bar breakout | TEST | 3,643 | 1,876/1,702/65 | 52.43% | +23.92 |
| Three-candle momentum | TRAIN | 14,264 | 7,211/6,853/200 | 51.27% | -218.88 |
| Three-candle momentum | VALIDATION | 4,289 | 2,158/2,044/87 | 51.36% | -58.64 |
| Three-candle momentum | TEST | 4,488 | 2,235/2,163/90 | 50.82% | -106.80 |
| Five-minute impulse | TRAIN | 8,588 | 4,489/4,018/81 | 52.77% | +111.88 |
| Five-minute impulse | VALIDATION | 1,978 | 1,029/924/25 | 52.69% | +22.68 |
| Five-minute impulse | TEST | 1,882 | 962/898/22 | 51.72% | -12.96 |
| RSI extreme crossing | TRAIN | 5,199 | 2,753/2,374/72 | 53.70% | +158.76 |
| RSI extreme crossing | VALIDATION | 1,473 | 764/685/24 | 52.73% | +17.88 |
| RSI extreme crossing | TEST | 1,510 | 803/673/34 | 54.40% | +65.76 |

## RSI exact matched-cohort check

For every accepted signal, inverse direction was evaluated on the same next-candle open and same signal-index +15 close as the original direction. The invariant was checked: direct outcome equals the negative of inverse outcome; draws remain draws. Counts and W/L/D match the canonical follow-up report exactly.

TEST month breakdown (inverse):

| Month | N | W/L/D | WR | Net @92% |
|---|---:|---:|---:|---:|
| 2026-08 | 360 | 215/134/11 | 61.60% | +63.80 |
| 2026-09 | 499 | 256/228/15 | 52.89% | +7.52 |
| 2026-10 | 549 | 278/263/8 | 51.39% | -7.24 |
| 2026-11 partial | 102 | 54/48/0 | 52.94% | +1.68 |

The TEST gain is heavily front-loaded in August. October is negative, and the November sample is small and incomplete.

## Date-block bootstrap stress test

To avoid treating 1,510 trades as independent Bernoulli trials, daily inverse wins/losses/draws were aggregated across the 92 calendar days from 2026-08-06 through 2026-11-05. Circular moving-block bootstrap resampled contiguous calendar-day blocks, preserving some short-range clustering. 30,000 replications per block length; deterministic seed 20261109 + block length.

Observed TEST: 803 wins, 673 losses, 34 draws; decisive WR 54.4038%; net +65.76 hypothetical units.

| Calendar block | 95% WR percentile interval | 95% net percentile interval | Bootstrap P(net ≤ 0) |
|---:|---:|---:|---:|
| 3 days | 52.15%–56.74% | +1.96 to +129.04 | 2.20% |
| 7 days | 51.77%–57.34% | -9.28 to +142.48 | 4.41% |
| 14 days | 51.24%–57.92% | -25.08 to +157.76 | 8.18% |
| 21 days | 51.04%–58.20% | -31.04 to +164.76 | 9.62% |

Interpretation: uncertainty widens materially as longer dependence blocks are preserved. For 7-, 14- and 21-day blocks, the 95% interval for net includes zero. The unadjusted 7-day bootstrap tail estimate is not a confirmatory p-value.

There were five rule families in this follow-up screen, and the broader research previously examined multiple RSI horizons and other variants. Even a rough Bonferroni adjustment across only five candidates would turn 4.41% into 22.05%; the true search family is larger and not fully enumerated. The evidence is therefore not statistically established after selection.

## Conclusion and next gate

1. The historical result is real and reproducible on the specified BID dataset.
2. The inverse RSI crossing rule is the strongest of these five 15-minute candidates, but it is not stable enough to call a reliable edge.
3. The monthly concentration and longer-block bootstrap intervals prevent a confident claim of positive expectancy.
4. The 92% payout is hypothetical and constant. Dukascopy BID candles are not Pocket Option executable quotes; spread, payout variation, quote-side mismatch, latency and settlement are absent.
5. No production code was changed and no live trading was performed.

Next gate: freeze RSI(14) 70/30 crossing inversion and 15-minute expiry without threshold or parameter tuning; capture all qualifying and rejected events prospectively on non-OTC EUR/USD Pocket Option DEMO, logging platform price, direction, displayed payout, decision/entry/expiry timestamps and measured delay. Evaluate only after a predeclared sample/time window. Manual analysis only; no automatic execution.

## Reproducibility

Script: `research/rsi_15m_block_bootstrap_validation.py`. It verifies the CSV SHA-256, reconstructs the Wilder RSI crossing schedule, asserts exact complementarity, and prints the split results plus block-bootstrap intervals.
