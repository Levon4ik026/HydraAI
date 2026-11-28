# Matched Inversion Screen — Follow-up 2026-11-09

## Status and scope

Exploratory historical research only. No production changes and no automated execution.

Dataset: `eurusd_research_clean.csv`; 486,488 M1 Dukascopy BID candles, 68 uninterrupted segments, 2025-07-21 15:11 UTC through 2026-11-05 16:08 UTC. SHA-256: `5ceac65aad0d2b27564d1fa68275ba968827271408e0c3ee95960f32e6ed296c`.

This follow-up independently re-runs several intentionally adverse indicator interpretations on one common, non-overlapping signal schedule. Each inverse is evaluated on the exact same accepted signal candles, entry prices and expiry prices as its direct rule. Thus inverse W/L are the direct rule's L/W and draws remain draws.

## Frozen mechanics

- Signal is known only after the signal candle closes.
- Entry: next M1 candle open.
- Expiry: close of signal candle index + 15 (15 minutes).
- One position per rule: after accepting a signal at index i, next eligible signal is at i+15 or later; no overlapping positions within a rule.
- Signals crossing a data gap or lacking entry/expiry data are discarded.
- CALL wins when expiry close > entry open; PUT wins when expiry close < entry open; equality is draw.
- Hypothetical payout +0.92 per win, -1 per loss, 0 draw. Decisive breakeven WR = 52.083%.
- TRAIN: signal timestamp before 2026-05-08; VALIDATION: 2026-05-08 through 2026-08-05; TEST: 2026-08-06 onward.
- WR excludes draws. Net units = 0.92 × wins − losses.

Rules:
1. EMA8/EMA21 crossover: CALL on cross above, PUT on cross below.
2. 20-bar breakout follow: CALL when close exceeds the prior 20-bar high; PUT when close falls below the prior 20-bar low.
3. Three-candle momentum follow: CALL after three consecutive bullish bodies; PUT after three consecutive bearish bodies.
4. Five-minute impulse follow: CALL if close/close[-5] − 1 ≥ 0.03%; PUT if ≤ −0.03%.
5. RSI(14) extreme-cross follow: CALL on crossing above 70; PUT on crossing below 30. RSI uses Wilder smoothing with an SMA seed per uninterrupted segment.

## Results — direct rule and exact inverse

Counts are accepted trades; W/L/D are shown in direct / inverse order. The inverse has the same trade count and exact same entry/expiry cohort.

| Rule | Split | N | Direct W/L/D | Direct WR | Direct net | Inverse W/L/D | Inverse WR | Inverse net |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| EMA8/21 cross | TRAIN | 8,449 | 4,085/4,239/125 | 49.07% | -480.80 | 4,239/4,085/125 | 50.93% | -185.12 |
| EMA8/21 cross | VALIDATION | 2,609 | 1,259/1,304/46 | 49.12% | -145.72 | 1,304/1,259/46 | 50.88% | -59.32 |
| EMA8/21 cross | TEST | 2,677 | 1,320/1,299/58 | 50.40% | -84.60 | 1,299/1,320/58 | 49.60% | -124.92 |
| 20-bar breakout | TRAIN | 11,916 | 5,570/6,177/169 | 47.42% | -1,052.60 | 6,177/5,570/169 | 52.58% | +112.84 |
| 20-bar breakout | VALIDATION | 3,553 | 1,699/1,785/69 | 48.77% | -221.92 | 1,785/1,699/69 | 51.23% | -56.80 |
| 20-bar breakout | TEST | 3,643 | 1,702/1,876/65 | 47.57% | -310.16 | 1,876/1,702/65 | 52.43% | +23.92 |
| Three-candle momentum | TRAIN | 14,264 | 6,853/7,211/200 | 48.73% | -906.24 | 7,211/6,853/200 | 51.27% | -218.88 |
| Three-candle momentum | VALIDATION | 4,289 | 2,044/2,158/87 | 48.64% | -277.52 | 2,158/2,044/87 | 51.36% | -58.64 |
| Three-candle momentum | TEST | 4,488 | 2,163/2,235/90 | 49.18% | -245.04 | 2,235/2,163/90 | 50.82% | -106.80 |
| 5m impulse 0.03% | TRAIN | 8,588 | 4,018/4,489/81 | 47.23% | -792.44 | 4,489/4,018/81 | 52.77% | +111.88 |
| 5m impulse 0.03% | VALIDATION | 1,978 | 924/1,029/25 | 47.31% | -178.92 | 1,029/924/25 | 52.69% | +22.68 |
| 5m impulse 0.03% | TEST | 1,882 | 898/962/22 | 48.28% | -135.84 | 962/898/22 | 51.72% | -12.96 |
| RSI extreme cross | TRAIN | 5,199 | 2,374/2,753/72 | 46.30% | -568.92 | 2,753/2,374/72 | 53.70% | +158.76 |
| RSI extreme cross | VALIDATION | 1,473 | 685/764/24 | 47.27% | -133.80 | 764/685/24 | 52.73% | +17.88 |
| RSI extreme cross | TEST | 1,510 | 673/803/34 | 45.60% | -183.84 | 803/673/34 | 54.40% | +65.76 |

## Monthly TEST results for inverse rules

| Rule | Month | N | W/L/D | WR | Net |
|---|---|---:|---:|---:|---:|
| RSI extreme cross | 2026-08 | 360 | 215/134/11 | 61.60% | +63.80 |
| RSI extreme cross | 2026-09 | 499 | 256/228/15 | 52.89% | +7.52 |
| RSI extreme cross | 2026-10 | 549 | 278/263/8 | 51.39% | -7.24 |
| RSI extreme cross | 2026-11 partial | 102 | 54/48/0 | 52.94% | +1.68 |
| 20-bar breakout | 2026-08 | 967 | 547/396/24 | 58.01% | +107.24 |
| 20-bar breakout | 2026-09 | 1,223 | 613/587/23 | 51.08% | -23.04 |
| 20-bar breakout | 2026-10 | 1,238 | 611/610/17 | 50.04% | -47.88 |
| 20-bar breakout | 2026-11 partial | 215 | 105/109/1 | 49.07% | -12.40 |
| 5m impulse 0.03% | 2026-08 | 344 | 179/161/4 | 52.65% | +3.68 |
| 5m impulse 0.03% | 2026-09 | 519 | 260/251/8 | 50.88% | -11.80 |
| 5m impulse 0.03% | 2026-10 | 843 | 441/392/10 | 52.94% | +13.72 |
| 5m impulse 0.03% | 2026-11 partial | 176 | 82/94/0 | 46.59% | -18.56 |
| Three-candle momentum | 2026-08 | 1,227 | 650/542/35 | 54.53% | +56.00 |
| Three-candle momentum | 2026-09 | 1,481 | 696/754/31 | 48.00% | -113.68 |
| Three-candle momentum | 2026-10 | 1,528 | 769/737/22 | 51.06% | -29.52 |
| Three-candle momentum | 2026-11 partial | 252 | 120/130/2 | 48.00% | -19.60 |
| EMA8/21 cross | 2026-08 | 762 | 377/363/22 | 50.95% | -16.16 |
| EMA8/21 cross | 2026-09 | 910 | 452/438/20 | 50.79% | -22.16 |
| EMA8/21 cross | 2026-10 | 866 | 401/449/16 | 47.18% | -80.08 |
| EMA8/21 cross | 2026-11 partial | 139 | 69/70/0 | 49.64% | -6.52 |

## Findings

- RSI extreme-cross follow is the only tested rule whose exact inverse clears the 92%-payout decisive breakeven threshold in TRAIN, VALIDATION and TEST. Inverse TEST: 54.40% decisive WR, +65.76 hypothetical units on 1,510 accepted trades.
- The RSI result is not uniformly strong by month: August is excellent, September only modestly positive, October negative, November is a small partial sample. This is not a stable monthly edge yet.
- 20-bar breakout inverse clears breakeven in TRAIN and TEST but fails VALIDATION; its monthly TEST result deteriorates sharply after August.
- Five-minute impulse inverse clears TRAIN and VALIDATION but fails TEST and November.
- Three-candle momentum and EMA crossover inverses do not beat payout breakeven in any split.
- A weak direct rule does not automatically yield a profitable inverse: payout hurdle matters, and regime stability matters.

## Limitations / next gate

This is a screened set of five rule families, not an untouched confirmatory experiment. Multiple-comparison/selection bias remains; trade outcomes overlap in calendar time across families and are serially dependent. The November sample is partial. The 92% payout is hypothetical and fixed. Data are Dukascopy BID candles, not Pocket Option executable quotes; platform quote differences, payout variation, latency, and settlement are not modeled. These historical results must not be interpreted as a live win-rate promise.

Do not tune thresholds on this TEST, promote any candidate into HydraAI production, or enable automatic execution. The sensible next step is to freeze RSI(14) 70/30 crossing inversion at one predeclared expiry and run a prospective non-OTC Pocket Option demo capture with actual payout and platform quotes, then use date-block inference on a genuinely fresh period.
