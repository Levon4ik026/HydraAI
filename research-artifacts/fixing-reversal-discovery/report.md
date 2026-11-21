# EUR/USD FX fixing and session-reversal discovery

- Captured UTC: 2026-11-15T08:01:33.034012+00:00
- Branch: hydra/research-validation
- Source: Dukascopy EUR/USD M1 BID; coverage 2024-01-01T22:00:00+00:00 — 2026-11-13T21:59:00+00:00
- Raw M1 rows: 1,068,882; valid unique: 1,068,882; invalid: 0; duplicate timestamps: 0
- Gaps: 3,643 intervals; 438,798 missing minutes; largest missing interval 2,944 minutes; continuity segments 3,644
- Raw CSV SHA-256: 1ab0157ed2507ce4e62bede90376736dbbe8ec271b0543e28752f37a1d7229f4
- Script SHA-256: 568012494b65a1b1aa591088b3446c96999264b5fceda26673f727565c642606
- Protocol SHA-256: 95c1c5afc5f79011176cf4de39b429ccd63bb9f37ca03c46734e1ed8ed7e3f0a
- Chronological calendar split: TRAIN before 2025-09-20; VALIDATION 2025-09-20–2026-04-16; TEST from 2026-04-17
- TEST is from a historical source period previously inspected by other HydraAI screens; it is exploratory, not pristine independent confirmation.
- Entry: exact next eligible M1 open; expiry: close of the 60th M1 candle from entry. Any missing minute in the 60-minute outcome window excludes the trade.
- Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u; decisive break-even WR 52.0833%.
- Matched control: opposite direction on the exact same candidate timestamps and prices.
- All five rules were frozen before this run; no parameter sweep or TEST-based tuning was performed.
- Dukascopy BID is not Pocket Option executable pricing; spread, quote construction, payout changes, latency and platform settlement are not modeled.

## Candidate results

| Candidate | Expiry | N | W/L/D | WR | Net @92% | Expectancy | Max DD | Longest L | VALIDATION N/WR/net | TEST N/WR/net | Status |
|---|---:|---:|---|---:|---:|---:|---:|---:|---|---|---|
| FXFIX-TOKYO-FADE-60 | 60m | 49 | 25/23/1 | 52.08% | +0.00u | +0.00u/trade | 9.64u | 6 | 9/12.50%/-6.08u | 3/33.33%/-1.08u | INSUFFICIENT_SAMPLE |

### FXFIX-TOKYO-FADE-60 — Tokyo

- Exact rule: Fade the completed EUR/USD return over 240 minutes before 09:55 Asia/Tokyo fixing; enter at fixing-time M1 open; 60-minute expiry.
- Market regime: fixing-time pre-move / post-fixing reversal
- Eligible windows: 49; raw triggers: 49; accepted trades: 49; excluded windows/trades: 701.
- Signal share: 100.000%; WAIT share: 0.000%; accepted trades after outcome availability: 49.
- Overall: N=49, W/L/D=25/23/1, decisive WR=52.08%, Wilson 95%=[38.329232303342806, 65.52868382304838], net=+0.00u, ROI=0.00%, expectancy=+0.00u/trade, PF=1.0, max DD=9.64u, longest loss streak=6.
- Matched continuation control on same timestamps: N=49, W/L/D=23/25/1, WR=47.92%, net=-3.84u.
- Candidate side split: CALL N=22 W/L/D=12/9/1 WR=57.14% net=+2.04u; PUT N=27 W/L/D=13/14/0 WR=48.15% net=-2.04u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 49, 'replicates': 2000, 'wr_95_pct': [38.297872340425535, 66.66666666666667], 'net_95_units': [-12.52, 13.440000000000001]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 37 | 23/14/0 | 62.16% | [46.100430439217654, 75.93600082420173] | +7.16u | 19.35% | 1.5114285714285713 | 4.24u | 4 |
| VALIDATION | 9 | 1/7/1 | 12.50% | [2.241749145005667, 47.08881822128535] | -6.08u | -67.56% | 0.13142857142857142 | 7.00u | 4 |
| TEST | 3 | 1/2/0 | 33.33% | [6.149194472039621, 79.23403991979522] | -1.08u | -36.00% | 0.46 | 2.00u | 2 |

| Payout | Net units |
|---:|---:|
| 50% | -10.50 |
| 60% | -8.00 |
| 70% | -5.50 |
| 80% | -3.00 |
| 85% | -1.75 |
| 90% | -0.50 |
| 92% | +0.00 |
| 95% | +0.75 |
| 100% | +2.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 2 | 0/2/0 | 0.00% | -2.00u |
| 2024-02 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2024-04 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2024-05 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2024-08 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2024-11 | 5 | 4/1/0 | 80.00% | +2.68u |
| 2024-12 | 2 | 2/0/0 | 100.00% | +1.84u |
| 2025-01 | 5 | 5/0/0 | 100.00% | +4.60u |
| 2025-02 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-03 | 4 | 0/4/0 | 0.00% | -4.00u |
| 2025-04 | 3 | 2/1/0 | 66.67% | +0.84u |
| 2025-05 | 5 | 3/2/0 | 60.00% | +0.76u |
| 2025-06 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-07 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2025-10 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-12 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-01 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-02 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-03 | 5 | 0/4/1 | 0.00% | -4.00u |
| 2026-10 | 3 | 1/2/0 | 33.33% | -1.08u |
| FXFIX-ECB-FADE-60 | 60m | 701 | 338/360/3 | 48.42% | -49.04u | -0.07u/trade | 59.96u | 10 | 141/46.10%/-16.20u | 147/44.52%/-21.20u | NOT_PASS_PRIMARY_SCREEN |

### FXFIX-ECB-FADE-60 — ECB Frankfurt

- Exact rule: Fade the completed EUR/USD return from 07:00 to 14:15 Europe/Berlin; enter at fixing-time M1 open; 60-minute expiry.
- Market regime: fixing-time pre-move / post-fixing reversal
- Eligible windows: 702; raw triggers: 701; accepted trades: 701; excluded windows/trades: 48.
- Signal share: 99.858%; WAIT share: 0.142%; accepted trades after outcome availability: 701.
- Overall: N=701, W/L/D=338/360/3, decisive WR=48.42%, Wilson 95%=[44.73540085021567, 52.12998808862436], net=-49.04u, ROI=-7.00%, expectancy=-0.07u/trade, PF=0.8637777777777779, max DD=59.96u, longest loss streak=10.
- Matched continuation control on same timestamps: N=701, W/L/D=360/338/3, WR=51.58%, net=-6.80u.
- Candidate side split: CALL N=362 W/L/D=174/188/0 WR=48.07% net=-27.92u; PUT N=339 W/L/D=164/172/3 WR=48.81% net=-21.12u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 701, 'replicates': 2000, 'wr_95_pct': [44.90674318507891, 52.1551724137931], 'net_95_units': [-96.19999999999999, 0.9600000000000364]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 413 | 208/203/2 | 50.61% | [45.7915310796401, 55.413748646791774] | -11.64u | -2.82% | 0.9426600985221676 | 23.44u | 9 |
| VALIDATION | 141 | 65/76/0 | 46.10% | [38.084142318172375, 54.321347042703636] | -16.20u | -11.49% | 0.7868421052631579 | 27.84u | 10 |
| TEST | 147 | 65/81/1 | 44.52% | [36.70225125367676, 52.619796111634756] | -21.20u | -14.42% | 0.7382716049382717 | 26.08u | 7 |

| Payout | Net units |
|---:|---:|
| 50% | -191.00 |
| 60% | -157.20 |
| 70% | -123.40 |
| 80% | -89.60 |
| 85% | -72.70 |
| 90% | -55.80 |
| 92% | -49.04 |
| 95% | -38.90 |
| 100% | -22.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 20 | 12/8/0 | 60.00% | +3.04u |
| 2024-02 | 20 | 11/9/0 | 55.00% | +1.12u |
| 2024-03 | 17 | 7/10/0 | 41.18% | -3.56u |
| 2024-04 | 14 | 9/5/0 | 64.29% | +3.28u |
| 2024-05 | 21 | 8/13/0 | 38.10% | -5.64u |
| 2024-06 | 20 | 10/10/0 | 50.00% | -0.80u |
| 2024-07 | 17 | 5/12/0 | 29.41% | -7.40u |
| 2024-08 | 21 | 8/12/1 | 40.00% | -4.64u |
| 2024-09 | 20 | 14/6/0 | 70.00% | +6.88u |
| 2024-10 | 20 | 11/9/0 | 55.00% | +1.12u |
| 2024-11 | 21 | 11/10/0 | 52.38% | +0.12u |
| 2024-12 | 20 | 8/11/1 | 42.11% | -3.64u |
| 2025-01 | 22 | 16/6/0 | 72.73% | +8.72u |
| 2025-02 | 19 | 11/8/0 | 57.89% | +2.12u |
| 2025-03 | 20 | 11/9/0 | 55.00% | +1.12u |
| 2025-04 | 21 | 8/13/0 | 38.10% | -5.64u |
| 2025-05 | 22 | 12/10/0 | 54.55% | +1.04u |
| 2025-06 | 21 | 4/17/0 | 19.05% | -13.32u |
| 2025-07 | 23 | 12/11/0 | 52.17% | +0.04u |
| 2025-08 | 20 | 14/6/0 | 70.00% | +6.88u |
| 2025-09 | 21 | 11/10/0 | 52.38% | +0.12u |
| 2025-10 | 23 | 15/8/0 | 65.22% | +5.80u |
| 2025-11 | 19 | 7/12/0 | 36.84% | -5.56u |
| 2025-12 | 20 | 9/11/0 | 45.00% | -2.72u |
| 2026-01 | 19 | 9/10/0 | 47.37% | -1.72u |
| 2026-02 | 20 | 5/15/0 | 25.00% | -10.40u |
| 2026-03 | 22 | 13/9/0 | 59.09% | +2.96u |
| 2026-04 | 21 | 7/14/0 | 33.33% | -7.56u |
| 2026-05 | 20 | 6/14/0 | 30.00% | -8.48u |
| 2026-06 | 21 | 11/10/0 | 52.38% | +0.12u |
| 2026-07 | 22 | 8/14/0 | 36.36% | -6.64u |
| 2026-08 | 21 | 10/11/0 | 47.62% | -1.80u |
| 2026-09 | 21 | 7/13/1 | 35.00% | -6.56u |
| 2026-10 | 22 | 13/9/0 | 59.09% | +2.96u |
| 2026-11 | 10 | 5/5/0 | 50.00% | -0.40u |
| FXFIX-LONDON-FADE-60 | 60m | 729 | 384/341/4 | 52.97% | +12.28u | +0.02u/trade | 31.96u | 6 | 144/55.94%/+10.60u | 150/48.67%/-9.84u | NOT_PASS_PRIMARY_SCREEN |

### FXFIX-LONDON-FADE-60 — London

- Exact rule: Fade the completed EUR/USD return from 07:00 to 16:00 Europe/London; enter at fixing-time M1 open; 60-minute expiry.
- Market regime: fixing-time pre-move / post-fixing reversal
- Eligible windows: 731; raw triggers: 729; accepted trades: 729; excluded windows/trades: 19.
- Signal share: 99.726%; WAIT share: 0.274%; accepted trades after outcome availability: 729.
- Overall: N=729, W/L/D=384/341/4, decisive WR=52.97%, Wilson 95%=[49.326285899774696, 56.573488252696855], net=+12.28u, ROI=1.68%, expectancy=+0.02u/trade, PF=1.0360117302052787, max DD=31.96u, longest loss streak=6.
- Matched continuation control on same timestamps: N=729, W/L/D=341/384/4, WR=47.03%, net=-70.28u.
- Candidate side split: CALL N=366 W/L/D=182/181/3 WR=50.14% net=-13.56u; PUT N=363 W/L/D=202/160/1 WR=55.80% net=+25.84u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 729, 'replicates': 2000, 'wr_95_pct': [49.17355371900826, 56.63029338393964], 'net_95_units': [-40.47999999999996, 63.20199999999998]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 435 | 231/201/3 | 53.47% | [48.75873478636636, 58.124502086319964] | +11.52u | 2.65% | 1.057313432835821 | 25.48u | 6 |
| VALIDATION | 144 | 80/63/1 | 55.94% | [47.757282816089145, 63.81982908168794] | +10.60u | 7.36% | 1.1682539682539683 | 8.16u | 5 |
| TEST | 150 | 73/77/0 | 48.67% | [40.80171192238753, 56.598208729260676] | -9.84u | -6.56% | 0.8722077922077922 | 14.16u | 4 |

| Payout | Net units |
|---:|---:|
| 50% | -149.00 |
| 60% | -110.60 |
| 70% | -72.20 |
| 80% | -33.80 |
| 85% | -14.60 |
| 90% | +4.60 |
| 92% | +12.28 |
| 95% | +23.80 |
| 100% | +43.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 22 | 12/10/0 | 54.55% | +1.04u |
| 2024-02 | 21 | 15/6/0 | 71.43% | +7.80u |
| 2024-03 | 19 | 10/7/2 | 58.82% | +2.20u |
| 2024-04 | 21 | 14/7/0 | 66.67% | +5.88u |
| 2024-05 | 23 | 15/8/0 | 65.22% | +5.80u |
| 2024-06 | 20 | 11/9/0 | 55.00% | +1.12u |
| 2024-07 | 20 | 15/5/0 | 75.00% | +8.80u |
| 2024-08 | 22 | 10/12/0 | 45.45% | -2.80u |
| 2024-09 | 20 | 10/9/1 | 52.63% | +0.20u |
| 2024-10 | 23 | 12/11/0 | 52.17% | +0.04u |
| 2024-11 | 21 | 8/13/0 | 38.10% | -5.64u |
| 2024-12 | 20 | 10/10/0 | 50.00% | -0.80u |
| 2025-01 | 22 | 12/10/0 | 54.55% | +1.04u |
| 2025-02 | 19 | 8/11/0 | 42.11% | -3.64u |
| 2025-03 | 20 | 11/9/0 | 55.00% | +1.12u |
| 2025-04 | 21 | 10/11/0 | 47.62% | -1.80u |
| 2025-05 | 22 | 9/13/0 | 40.91% | -4.72u |
| 2025-06 | 21 | 13/8/0 | 61.90% | +3.96u |
| 2025-07 | 22 | 10/12/0 | 45.45% | -2.80u |
| 2025-08 | 21 | 12/9/0 | 57.14% | +2.04u |
| 2025-09 | 22 | 7/15/0 | 31.82% | -8.56u |
| 2025-10 | 23 | 12/11/0 | 52.17% | +0.04u |
| 2025-11 | 20 | 10/10/0 | 50.00% | -0.80u |
| 2025-12 | 21 | 14/6/1 | 70.00% | +6.88u |
| 2026-01 | 20 | 8/12/0 | 40.00% | -4.64u |
| 2026-02 | 20 | 14/6/0 | 70.00% | +6.88u |
| 2026-03 | 22 | 11/11/0 | 50.00% | -0.88u |
| 2026-04 | 21 | 13/8/0 | 61.90% | +3.96u |
| 2026-05 | 21 | 8/13/0 | 38.10% | -5.64u |
| 2026-06 | 22 | 10/12/0 | 45.45% | -2.80u |
| 2026-07 | 22 | 12/10/0 | 54.55% | +1.04u |
| 2026-08 | 21 | 10/11/0 | 47.62% | -1.80u |
| 2026-09 | 22 | 13/9/0 | 59.09% | +2.96u |
| 2026-10 | 22 | 10/12/0 | 45.45% | -2.80u |
| 2026-11 | 10 | 5/5/0 | 50.00% | -0.40u |
| NY17-DAILY-SHOCK-FADE-60 | 60m | 36 | 26/10/0 | 72.22% | +13.92u | +0.39u/trade | 3.24u | 3 | 10/50.00%/-0.40u | 2/50.00%/-0.08u | INSUFFICIENT_SAMPLE |

### NY17-DAILY-SHOCK-FADE-60 — NY 17:00 daily shock fade

- Exact rule: Completed 17:00–17:00 New York session absolute log return >= 1.5x mean absolute return of preceding 20 valid sessions (current excluded); fade at next 17:00 NY open; 60-minute expiry.
- Market regime: large completed NY trading-session move
- Eligible windows: 131; raw triggers: 36; accepted trades: 36; excluded windows/trades: 512.
- Signal share: 27.481%; WAIT share: 72.519%; accepted trades after outcome availability: 36.
- Overall: N=36, W/L/D=26/10/0, decisive WR=72.22%, Wilson 95%=[56.00751000260289, 84.1516620598654], net=+13.92u, ROI=38.67%, expectancy=+0.39u/trade, PF=2.3920000000000003, max DD=3.24u, longest loss streak=3.
- Matched continuation control on same timestamps: N=36, W/L/D=10/26/0, WR=27.78%, net=-16.80u.
- Candidate side split: CALL N=17 W/L/D=13/4/0 WR=76.47% net=+7.96u; PUT N=19 W/L/D=13/6/0 WR=68.42% net=+5.96u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 36, 'replicates': 2000, 'wr_95_pct': [58.333333333333336, 86.11111111111111], 'net_95_units': [4.32, 23.52]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 24 | 20/4/0 | 83.33% | [64.14692935030095, 93.32132367136705] | +14.40u | 60.00% | 4.6000000000000005 | 2.00u | 2 |
| VALIDATION | 10 | 5/5/0 | 50.00% | [23.6593090512564, 76.3406909487436] | -0.40u | -4.00% | 0.9200000000000002 | 3.16u | 3 |
| TEST | 2 | 1/1/0 | 50.00% | [9.453120573423075, 90.54687942657694] | -0.08u | -4.00% | 0.92 | 1.00u | 1 |

| Payout | Net units |
|---:|---:|
| 50% | +3.00 |
| 60% | +5.60 |
| 70% | +8.20 |
| 80% | +10.80 |
| 85% | +12.10 |
| 90% | +13.40 |
| 92% | +13.92 |
| 95% | +14.70 |
| 100% | +16.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-02 | 3 | 2/1/0 | 66.67% | +0.84u |
| 2024-03 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2024-04 | 2 | 2/0/0 | 100.00% | +1.84u |
| 2024-06 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2024-07 | 2 | 2/0/0 | 100.00% | +1.84u |
| 2024-08 | 2 | 2/0/0 | 100.00% | +1.84u |
| 2024-11 | 3 | 2/1/0 | 66.67% | +0.84u |
| 2025-02 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-03 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-04 | 2 | 2/0/0 | 100.00% | +1.84u |
| 2025-06 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2025-07 | 3 | 2/1/0 | 66.67% | +0.84u |
| 2025-08 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-09 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-11 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-12 | 4 | 2/2/0 | 50.00% | -0.16u |
| 2026-01 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2026-03 | 4 | 1/3/0 | 25.00% | -2.08u |
| 2026-10 | 2 | 1/1/0 | 50.00% | -0.08u |
| NY17-WEEKLY-SHOCK-FADE-60 | 60m | 9 | 3/6/0 | 33.33% | -3.24u | -0.36u/trade | 5.08u | 5 | 4/25.00%/-2.08u | 0/n/a/+0.00u | INSUFFICIENT_SAMPLE |

### NY17-WEEKLY-SHOCK-FADE-60 — NY Sunday–Friday weekly shock fade

- Exact rule: Completed Sunday 17:00–Friday 17:00 New York session absolute log return >= 1.0x mean absolute return of preceding 13 valid weeks (current excluded); fade at next Sunday 17:00 NY open; 60-minute expiry.
- Market regime: large completed NY trading-week move
- Eligible windows: 19; raw triggers: 9; accepted trades: 9; excluded windows/trades: 82.
- Signal share: 47.368%; WAIT share: 52.632%; accepted trades after outcome availability: 9.
- Overall: N=9, W/L/D=3/6/0, decisive WR=33.33%, Wilson 95%=[12.05838183869109, 64.57978644196037], net=-3.24u, ROI=-36.00%, expectancy=-0.36u/trade, PF=0.46, max DD=5.08u, longest loss streak=5.
- Matched continuation control on same timestamps: N=9, W/L/D=6/3/0, WR=66.67%, net=+2.52u.
- Candidate side split: CALL N=4 W/L/D=1/3/0 WR=25.00% net=-2.08u; PUT N=5 W/L/D=2/3/0 WR=40.00% net=-1.16u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 9, 'replicates': 2000, 'wr_95_pct': [0.0, 66.66666666666667], 'net_95_units': [-9.0, 2.5200000000000005]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 5 | 2/3/0 | 40.00% | [11.762077423264783, 76.9275718723987] | -1.16u | -23.20% | 0.6133333333333334 | 2.08u | 2 |
| VALIDATION | 4 | 1/3/0 | 25.00% | [4.558726080970055, 69.93581574175981] | -2.08u | -52.00% | 0.3066666666666667 | 3.00u | 3 |
| TEST | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |

| Payout | Net units |
|---:|---:|
| 50% | -4.50 |
| 60% | -4.20 |
| 70% | -3.90 |
| 80% | -3.60 |
| 85% | -3.45 |
| 90% | -3.30 |
| 92% | -3.24 |
| 95% | -3.15 |
| 100% | -3.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-08 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2024-11 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2025-01 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2025-04 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2025-08 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2025-12 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-01 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-03 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-04 | 1 | 1/0/0 | 100.00% | +0.92u |

## Primary screening outcome

- Preliminary leads passing the fixed screen: 0/5 — none.
- A passing row is only a preliminary historical lead. The source period was previously inspected by other research; no row is independently confirmed. Fresh prospective observations and Pocket Option DEMO quote/settlement validation remain mandatory.
- Do not fill a five-candidate batch with under-sampled or negative rows.

## Interpretation limits

- Wilson intervals assume independent trades. Day-cluster bootstrap preserves within-day clustering but does not remove multi-day dependence or broad research-selection bias.
- The five candidate families are not pooled. The matched continuation control is the opposite direction at identical timestamps, not a randomized experiment.
- M1 BID candles do not model the Pocket Option executable quote, spread, latency, payout variation or platform settlement. A positive historical proxy result is not a claim of platform profitability.

## Reproducibility

- Machine-readable manifest: manifest.json
- Trade-level ledger: trades.csv
