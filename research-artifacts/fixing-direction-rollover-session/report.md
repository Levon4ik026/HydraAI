# EUR/USD direct fixing and rollover-excluded session discovery

- Captured UTC: 2026-11-15T08:12:25.053493+00:00
- Branch: hydra/research-validation
- Source: Dukascopy EUR/USD M1 BID; coverage 2024-01-01T22:00:00+00:00 — 2026-11-13T21:59:00+00:00
- Raw M1 rows: 1,068,881; valid unique: 1,068,881; invalid: 0; duplicate timestamps: 0
- Gaps: 3,644 intervals; 438,799 missing minutes; largest missing interval 2,944 minutes; continuity segments 3,645
- Raw CSV SHA-256: 32ab8005153803e0554c4f248b4f77763c1aa5325982bc95087c719a3e849e50
- Script SHA-256: 405c605565dbfbefb82642d3269dc3b0b6a98e5641c1e23ec3eaa7d8a742cdf4
- Protocol SHA-256: bf769c340b0d8ae15c14e452dbdf107833081377b0989428d396a9d63a9089f4
- Calendar split: TRAIN before 2025-09-20; VALIDATION 2025-09-20–2026-04-16; TEST from 2026-04-17
- Historical TEST is from a source period previously inspected by other HydraAI screens; it is exploratory, not pristine independent confirmation.
- Expiry selection uses TRAIN only: N>=30, positive net at 92%, decisive WR above 52.0833%; maximize Wilson 95% lower bound, then net, then shorter expiry.
- All entries use exact M1 opens; expiry settles at the close of the final included M1 bar. Missing outcome minutes exclude the trade.
- Payout accounting: WIN +0.92u, LOSS -1u, DRAW 0u. Matched control is the opposite direction at the same timestamps.
- Dukascopy BID is not Pocket Option executable pricing; spread, quote construction, platform payout, latency and settlement are not modeled.

## Candidate results

| Candidate | Selected expiry | N | W/L/D | WR | Net @92% | Max DD | VALIDATION N/WR/net | TEST N/WR/net | Status |
|---|---:|---:|---|---:|---:|---:|---|---|---|
| FXFIX-TOKYO-PREFIX-USD-REV-CALL | none | 0 | 0/0/0 | n/a | +0.00u | 0.00u | 0/n/a/+0.00u | 0/n/a/+0.00u | NO_TRAIN_VARIANT_PASS |

### FXFIX-TOKYO-PREFIX-USD-REV-CALL — Tokyo

- Exact rule: Pre-window from 17:00 America/New_York on the NY local date of the Tokyo fixing to 09:55 Asia/Tokyo; if completed EUR/USD log return < 0, CALL at fixing-time M1 open; otherwise WAIT.
- Market regime: USD-strength pre-fix / post-fix reversal
- Eligible windows: 82; raw triggers: 39; excluded/quality-rejected windows: 670.
- Signal share: 47.561%; WAIT share: 52.439%.
- TRAIN expiry selection: no eligible expiry using Wilson lower bound; no VALIDATION/TEST metric was used for selection.

| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |
|---:|---:|---|---:|---:|---:|---|
| 5m | 25 | 13/11/1 | 54.17% | +0.96u | 35.07% | no |
| 10m | 25 | 14/11/0 | 56.00% | +1.88u | 37.07% | no |
| 15m | 25 | 15/10/0 | 60.00% | +3.80u | 40.74% | no |
| 20m | 25 | 14/11/0 | 56.00% | +1.88u | 37.07% | no |
| 30m | 25 | 16/9/0 | 64.00% | +5.72u | 44.52% | no |
| 60m | 25 | 14/11/0 | 56.00% | +1.88u | 37.07% | no |

- Selected-expiry overall: N=0, W/L/D=0/0/0, WR=n/a, Wilson 95%=None, net=+0.00u, ROI=n/a, expectancy=n/a/trade, PF=None, max DD=0.00u, longest losing streak=0.
- Matched opposite-direction control: N=0, W/L/D=0/0/0, WR=n/a, net=+0.00u.
- Candidate side split: CALL N=0 WR=n/a net=+0.00u; PUT N=0 WR=n/a net=+0.00u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 0, 'replicates': 0, 'wr_95_pct': None, 'net_95_units': None}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |
| VALIDATION | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |
| TEST | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |

| Payout | Net units |
|---:|---:|
| 50% | +0.00 |
| 60% | +0.00 |
| 70% | +0.00 |
| 80% | +0.00 |
| 85% | +0.00 |
| 90% | +0.00 |
| 92% | +0.00 |
| 95% | +0.00 |
| 100% | +0.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| FXFIX-ECB-PREFIX-USD-REV-CALL | 20 | 362 | 175/186/1 | 48.48% | -25.00u | 35.96u | 84/47.62%/-7.20u | 81/38.27%/-21.48u | NOT_PASS_PRIMARY_SCREEN |

### FXFIX-ECB-PREFIX-USD-REV-CALL — ECB Frankfurt

- Exact rule: Pre-window from 07:00 to 14:15 Europe/Berlin; if completed EUR/USD log return < 0, CALL at fixing-time M1 open; otherwise WAIT.
- Market regime: USD-strength pre-fix / post-fix reversal
- Eligible windows: 702; raw triggers: 362; excluded/quality-rejected windows: 50.
- Signal share: 51.567%; WAIT share: 48.433%.
- TRAIN expiry selection: 20 using Wilson lower bound; no VALIDATION/TEST metric was used for selection.

| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |
|---:|---:|---|---:|---:|---:|---|
| 5m | 197 | 95/102/0 | 48.22% | -14.60u | 41.35% | no |
| 10m | 197 | 94/101/2 | 48.21% | -14.52u | 41.29% | no |
| 15m | 197 | 86/109/2 | 44.10% | -29.88u | 37.31% | no |
| 20m | 197 | 104/92/1 | 53.06% | +3.68u | 46.08% | yes |
| 30m | 197 | 93/104/0 | 47.21% | -18.44u | 40.36% | no |
| 60m | 197 | 99/98/0 | 50.25% | -6.92u | 43.33% | no |

- Selected-expiry overall: N=362, W/L/D=175/186/1, WR=48.48%, Wilson 95%=[43.36427859649632, 53.620713176216086], net=-25.00u, ROI=-6.91%, expectancy=-0.07u/trade, PF=0.8655913978494624, max DD=35.96u, longest losing streak=7.
- Matched opposite-direction control: N=362, W/L/D=186/175/1, WR=51.52%, net=-3.88u.
- Candidate side split: CALL N=362 WR=48.48% net=-25.00u; PUT N=0 WR=n/a net=+0.00u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 362, 'replicates': 2000, 'wr_95_pct': [43.45194216593053, 53.76311962326289], 'net_95_units': [-59.583, 11.580999999999888]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 197 | 104/92/1 | 53.06% | [46.08286728390604, 59.921892724760085] | +3.68u | 1.87% | 1.04 | 17.24u | 7 |
| VALIDATION | 84 | 40/44/0 | 47.62% | [37.27844721560723, 58.16789434827211] | -7.20u | -8.57% | 0.8363636363636364 | 13.64u | 6 |
| TEST | 81 | 31/50/0 | 38.27% | [28.446535970964614, 49.15875245275869] | -21.48u | -26.52% | 0.5704 | 24.36u | 6 |

| Payout | Net units |
|---:|---:|
| 50% | -98.50 |
| 60% | -81.00 |
| 70% | -63.50 |
| 80% | -46.00 |
| 85% | -37.25 |
| 90% | -28.50 |
| 92% | -25.00 |
| 95% | -19.75 |
| 100% | -11.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 10 | 5/4/1 | 55.56% | +0.60u |
| 2024-02 | 9 | 2/7/0 | 22.22% | -5.16u |
| 2024-03 | 10 | 2/8/0 | 20.00% | -6.16u |
| 2024-04 | 4 | 2/2/0 | 50.00% | -0.16u |
| 2024-05 | 6 | 5/1/0 | 83.33% | +3.60u |
| 2024-06 | 13 | 7/6/0 | 53.85% | +0.44u |
| 2024-07 | 5 | 2/3/0 | 40.00% | -1.16u |
| 2024-08 | 10 | 2/8/0 | 20.00% | -6.16u |
| 2024-09 | 8 | 5/3/0 | 62.50% | +1.60u |
| 2024-10 | 10 | 6/4/0 | 60.00% | +1.52u |
| 2024-11 | 11 | 6/5/0 | 54.55% | +0.52u |
| 2024-12 | 9 | 6/3/0 | 66.67% | +2.52u |
| 2025-01 | 11 | 10/1/0 | 90.91% | +8.20u |
| 2025-02 | 7 | 5/2/0 | 71.43% | +2.60u |
| 2025-03 | 8 | 4/4/0 | 50.00% | -0.32u |
| 2025-04 | 10 | 7/3/0 | 70.00% | +3.44u |
| 2025-05 | 11 | 6/5/0 | 54.55% | +0.52u |
| 2025-06 | 9 | 4/5/0 | 44.44% | -1.32u |
| 2025-07 | 16 | 6/10/0 | 37.50% | -4.48u |
| 2025-08 | 12 | 9/3/0 | 75.00% | +5.28u |
| 2025-09 | 13 | 3/10/0 | 23.08% | -7.24u |
| 2025-10 | 16 | 8/8/0 | 50.00% | -0.64u |
| 2025-11 | 12 | 7/5/0 | 58.33% | +1.44u |
| 2025-12 | 9 | 7/2/0 | 77.78% | +4.44u |
| 2026-01 | 13 | 5/8/0 | 38.46% | -3.40u |
| 2026-02 | 15 | 4/11/0 | 26.67% | -7.32u |
| 2026-03 | 11 | 6/5/0 | 54.55% | +0.52u |
| 2026-04 | 9 | 5/4/0 | 55.56% | +0.60u |
| 2026-05 | 8 | 5/3/0 | 62.50% | +1.60u |
| 2026-06 | 10 | 6/4/0 | 60.00% | +1.52u |
| 2026-07 | 15 | 3/12/0 | 20.00% | -9.24u |
| 2026-08 | 6 | 4/2/0 | 66.67% | +1.68u |
| 2026-09 | 13 | 4/9/0 | 30.77% | -5.32u |
| 2026-10 | 16 | 4/12/0 | 25.00% | -8.32u |
| 2026-11 | 7 | 3/4/0 | 42.86% | -1.24u |
| FXFIX-LONDON-PREFIX-USD-REV-CALL | 30 | 366 | 195/169/2 | 53.57% | +10.40u | 16.60u | 73/54.79%/+3.80u | 76/42.67%/-13.56u | NOT_PASS_PRIMARY_SCREEN |

### FXFIX-LONDON-PREFIX-USD-REV-CALL — London

- Exact rule: Pre-window from 07:00 to 16:00 Europe/London; if completed EUR/USD log return < 0, CALL at fixing-time M1 open; otherwise WAIT.
- Market regime: USD-strength pre-fix / post-fix reversal
- Eligible windows: 731; raw triggers: 366; excluded/quality-rejected windows: 21.
- Signal share: 50.068%; WAIT share: 49.932%.
- TRAIN expiry selection: 30 using Wilson lower bound; no VALIDATION/TEST metric was used for selection.

| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |
|---:|---:|---|---:|---:|---:|---|
| 5m | 217 | 108/107/2 | 50.23% | -7.64u | 43.60% | no |
| 10m | 217 | 100/115/2 | 46.51% | -23.00u | 39.96% | no |
| 15m | 217 | 112/105/0 | 51.61% | -1.96u | 44.99% | no |
| 20m | 217 | 109/107/1 | 50.46% | -6.72u | 43.85% | no |
| 30m | 217 | 123/93/1 | 56.94% | +20.16u | 50.28% | yes |
| 60m | 217 | 110/105/2 | 51.16% | -3.80u | 44.52% | no |

- Selected-expiry overall: N=366, W/L/D=195/169/2, WR=53.57%, Wilson 95%=[48.437436132680986, 58.630826396332566], net=+10.40u, ROI=2.84%, expectancy=+0.03u/trade, PF=1.0615384615384615, max DD=16.60u, longest losing streak=7.
- Matched opposite-direction control: N=366, W/L/D=169/195/2, WR=46.43%, net=-39.52u.
- Candidate side split: CALL N=366 WR=53.57% net=+10.40u; PUT N=0 WR=n/a net=+0.00u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 366, 'replicates': 2000, 'wr_95_pct': [48.49294312992943, 59.01639344262295], 'net_95_units': [-25.081999999999983, 48.72]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 217 | 123/93/1 | 56.94% | [50.2766136008876, 63.36958405488233] | +20.16u | 9.29% | 1.2167741935483871 | 12.96u | 5 |
| VALIDATION | 73 | 40/33/0 | 54.79% | [43.42432150980831, 65.68534416732852] | +3.80u | 5.21% | 1.1151515151515152 | 8.40u | 6 |
| TEST | 76 | 32/43/1 | 42.67% | [32.10074201902476, 53.947207670723074] | -13.56u | -17.84% | 0.6846511627906977 | 15.32u | 6 |

| Payout | Net units |
|---:|---:|
| 50% | -71.50 |
| 60% | -52.00 |
| 70% | -32.50 |
| 80% | -13.00 |
| 85% | -3.25 |
| 90% | +6.50 |
| 92% | +10.40 |
| 95% | +16.25 |
| 100% | +26.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 13 | 13/0/0 | 100.00% | +11.96u |
| 2024-02 | 13 | 10/3/0 | 76.92% | +6.20u |
| 2024-03 | 10 | 6/4/0 | 60.00% | +1.52u |
| 2024-04 | 13 | 7/6/0 | 53.85% | +0.44u |
| 2024-05 | 7 | 4/3/0 | 57.14% | +0.68u |
| 2024-06 | 12 | 9/3/0 | 75.00% | +5.28u |
| 2024-07 | 8 | 3/5/0 | 37.50% | -2.24u |
| 2024-08 | 10 | 3/7/0 | 30.00% | -4.24u |
| 2024-09 | 13 | 7/6/0 | 53.85% | +0.44u |
| 2024-10 | 14 | 7/7/0 | 50.00% | -0.56u |
| 2024-11 | 11 | 4/7/0 | 36.36% | -3.32u |
| 2024-12 | 12 | 6/5/1 | 54.55% | +0.52u |
| 2025-01 | 9 | 4/5/0 | 44.44% | -1.32u |
| 2025-02 | 7 | 3/4/0 | 42.86% | -1.24u |
| 2025-03 | 8 | 7/1/0 | 87.50% | +5.44u |
| 2025-04 | 12 | 7/5/0 | 58.33% | +1.44u |
| 2025-05 | 9 | 2/7/0 | 22.22% | -5.16u |
| 2025-06 | 5 | 3/2/0 | 60.00% | +0.76u |
| 2025-07 | 15 | 9/6/0 | 60.00% | +2.28u |
| 2025-08 | 8 | 6/2/0 | 75.00% | +3.52u |
| 2025-09 | 11 | 3/8/0 | 27.27% | -5.24u |
| 2025-10 | 12 | 6/6/0 | 50.00% | -0.48u |
| 2025-11 | 9 | 6/3/0 | 66.67% | +2.52u |
| 2025-12 | 10 | 5/5/0 | 50.00% | -0.40u |
| 2026-01 | 11 | 4/7/0 | 36.36% | -3.32u |
| 2026-02 | 13 | 9/4/0 | 69.23% | +4.28u |
| 2026-03 | 14 | 9/5/0 | 64.29% | +3.28u |
| 2026-04 | 4 | 3/1/0 | 75.00% | +1.76u |
| 2026-05 | 10 | 4/6/0 | 40.00% | -2.32u |
| 2026-06 | 11 | 5/6/0 | 45.45% | -1.40u |
| 2026-07 | 13 | 6/7/0 | 46.15% | -1.48u |
| 2026-08 | 9 | 4/5/0 | 44.44% | -1.32u |
| 2026-09 | 12 | 4/8/0 | 33.33% | -4.32u |
| 2026-10 | 12 | 5/6/1 | 45.45% | -1.40u |
| 2026-11 | 6 | 2/4/0 | 33.33% | -2.16u |
| NY18-DAILY-SHOCK-FADE | 30 | 125 | 64/59/2 | 52.03% | -0.12u | 11.84u | 34/50.00%/-1.36u | 20/55.00%/+1.12u | INSUFFICIENT_SAMPLE |

### NY18-DAILY-SHOCK-FADE — NY rollover-excluded daily shock fade

- Exact rule: Completed 18:00–17:00 New York session absolute log return >=1.0x mean absolute return of preceding 20 valid sessions (current excluded); fade at next 18:00 NY open.
- Market regime: large completed rollover-excluded NY daily session move
- Eligible windows: 264; raw triggers: 125; excluded/quality-rejected windows: 502.
- Signal share: 47.348%; WAIT share: 52.652%.
- TRAIN expiry selection: 30 using Wilson lower bound; no VALIDATION/TEST metric was used for selection.

| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |
|---:|---:|---|---:|---:|---:|---|
| 5m | 71 | 31/40/0 | 43.66% | -11.48u | 32.75% | no |
| 10m | 71 | 35/33/3 | 51.47% | -0.80u | 39.83% | no |
| 15m | 71 | 35/34/2 | 50.72% | -1.80u | 39.21% | no |
| 20m | 71 | 33/36/2 | 47.83% | -5.64u | 36.47% | no |
| 30m | 71 | 36/33/2 | 52.17% | +0.12u | 40.59% | yes |
| 60m | 71 | 30/41/0 | 42.25% | -13.40u | 31.45% | no |

- Selected-expiry overall: N=125, W/L/D=64/59/2, WR=52.03%, Wilson 95%=[43.27657187957635, 60.66535692389802], net=-0.12u, ROI=-0.10%, expectancy=-0.00u/trade, PF=0.9979661016949153, max DD=11.84u, longest losing streak=9.
- Matched opposite-direction control: N=125, W/L/D=59/64/2, WR=47.97%, net=-9.72u.
- Candidate side split: CALL N=62 WR=67.74% net=+18.64u; PUT N=63 WR=36.07% net=-18.76u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 125, 'replicates': 2000, 'wr_95_pct': [43.19723577235773, 61.16035723806983], 'net_95_units': [-21.239999999999995, 21.100999999999885]}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 71 | 36/33/2 | 52.17% | [40.58725487361115, 63.53127878643645] | +0.12u | 0.17% | 1.0036363636363639 | 9.00u | 9 |
| VALIDATION | 34 | 17/17/0 | 50.00% | [34.0693256456825, 65.9306743543175] | -1.36u | -4.00% | 0.92 | 5.48u | 4 |
| TEST | 20 | 11/9/0 | 55.00% | [34.20853424503424, 74.18021417443758] | +1.12u | 5.60% | 1.1244444444444446 | 5.08u | 4 |

| Payout | Net units |
|---:|---:|
| 50% | -27.00 |
| 60% | -20.60 |
| 70% | -14.20 |
| 80% | -7.80 |
| 85% | -4.60 |
| 90% | -1.40 |
| 92% | -0.12 |
| 95% | +1.80 |
| 100% | +5.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|
| 2024-01 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2024-03 | 2 | 0/2/0 | 0.00% | -2.00u |
| 2024-04 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2024-05 | 2 | 0/2/0 | 0.00% | -2.00u |
| 2024-06 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2024-08 | 3 | 0/2/1 | 0.00% | -2.00u |
| 2024-09 | 3 | 3/0/0 | 100.00% | +2.76u |
| 2024-10 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2024-11 | 8 | 8/0/0 | 100.00% | +7.36u |
| 2024-12 | 3 | 3/0/0 | 100.00% | +2.76u |
| 2025-01 | 4 | 3/1/0 | 75.00% | +1.76u |
| 2025-02 | 6 | 4/2/0 | 66.67% | +1.68u |
| 2025-03 | 5 | 2/3/0 | 40.00% | -1.16u |
| 2025-04 | 6 | 2/4/0 | 33.33% | -2.16u |
| 2025-05 | 8 | 5/3/0 | 62.50% | +1.60u |
| 2025-06 | 8 | 1/6/1 | 14.29% | -5.08u |
| 2025-07 | 4 | 3/1/0 | 75.00% | +1.76u |
| 2025-08 | 2 | 0/2/0 | 0.00% | -2.00u |
| 2025-09 | 3 | 2/1/0 | 66.67% | +0.84u |
| 2025-10 | 5 | 1/4/0 | 20.00% | -3.08u |
| 2025-11 | 5 | 3/2/0 | 60.00% | +0.76u |
| 2025-12 | 2 | 0/2/0 | 0.00% | -2.00u |
| 2026-01 | 7 | 4/3/0 | 57.14% | +0.68u |
| 2026-02 | 3 | 3/0/0 | 100.00% | +2.76u |
| 2026-03 | 9 | 4/5/0 | 44.44% | -1.32u |
| 2026-04 | 2 | 1/1/0 | 50.00% | -0.08u |
| 2026-05 | 4 | 3/1/0 | 75.00% | +1.76u |
| 2026-06 | 3 | 1/2/0 | 33.33% | -1.08u |
| 2026-07 | 4 | 1/3/0 | 25.00% | -2.08u |
| 2026-08 | 1 | 0/1/0 | 0.00% | -1.00u |
| 2026-09 | 1 | 1/0/0 | 100.00% | +0.92u |
| 2026-10 | 6 | 5/1/0 | 83.33% | +3.60u |
| 2026-11 | 1 | 0/1/0 | 0.00% | -1.00u |
| NY18-WEEKLY-SHOCK-FADE | none | 0 | 0/0/0 | n/a | +0.00u | 0.00u | 0/n/a/+0.00u | 0/n/a/+0.00u | NO_TRAIN_VARIANT_PASS |

### NY18-WEEKLY-SHOCK-FADE — NY rollover-excluded weekly shock fade

- Exact rule: Completed Sunday 18:00–Friday 17:00 New York week absolute log return >=0.75x mean absolute return of preceding 13 valid weeks (current excluded); fade at next Sunday 18:00 NY open.
- Market regime: large completed rollover-excluded NY trading-week move
- Eligible windows: 105; raw triggers: 54; excluded/quality-rejected windows: 39.
- Signal share: 51.429%; WAIT share: 48.571%.
- TRAIN expiry selection: no eligible expiry using Wilson lower bound; no VALIDATION/TEST metric was used for selection.

| Expiry | TRAIN N | W/L/D | WR | Net @92% | Wilson lower | Eligible for selection |
|---:|---:|---|---:|---:|---:|---|
| 5m | 29 | 17/12/0 | 58.62% | +3.64u | 40.74% | no |
| 10m | 29 | 17/12/0 | 58.62% | +3.64u | 40.74% | no |
| 15m | 29 | 16/13/0 | 55.17% | +1.72u | 37.55% | no |
| 20m | 29 | 18/11/0 | 62.07% | +5.56u | 44.00% | no |
| 30m | 29 | 17/12/0 | 58.62% | +3.64u | 40.74% | no |
| 60m | 29 | 15/13/1 | 53.57% | +0.80u | 35.81% | no |

- Selected-expiry overall: N=0, W/L/D=0/0/0, WR=n/a, Wilson 95%=None, net=+0.00u, ROI=n/a, expectancy=n/a/trade, PF=None, max DD=0.00u, longest losing streak=0.
- Matched opposite-direction control: N=0, W/L/D=0/0/0, WR=n/a, net=+0.00u.
- Candidate side split: CALL N=0 WR=n/a net=+0.00u; PUT N=0 WR=n/a net=+0.00u.
- Day-cluster bootstrap (2,000 reps, seed 20261115): {'days': 0, 'replicates': 0, 'wr_95_pct': None, 'net_95_units': None}.
- Split purges: TRAIN=0, VALIDATION=0.

| Split | N | W/L/D | WR | Wilson 95% | Net @92% | ROI | PF | Max DD | Max loss streak |
|---|---:|---|---:|---|---:|---:|---:|---:|---:|
| TRAIN | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |
| VALIDATION | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |
| TEST | 0 | 0/0/0 | n/a | None | +0.00u | n/a | None | 0.00u | 0 |

| Payout | Net units |
|---:|---:|
| 50% | +0.00 |
| 60% | +0.00 |
| 70% | +0.00 |
| 80% | +0.00 |
| 85% | +0.00 |
| 90% | +0.00 |
| 92% | +0.00 |
| 95% | +0.00 |
| 100% | +0.00 |

| UTC month | N | W/L/D | WR | Net @92% |
|---|---:|---|---:|---:|

## Primary screening outcome

- Preliminary leads passing the fixed screen: 0/5 — none.
- Passing is preliminary only. Historical TEST is from a previously inspected source period; prospective validation and Pocket Option DEMO quote/settlement comparison remain mandatory.
- Do not fill a five-candidate batch with under-sampled or negative rows.

## Interpretation limits

- Expiry selection is TRAIN-only. The selected VALIDATION/TEST rows are not used to choose expiry.
- Wilson intervals assume independent outcomes; day-cluster bootstrap preserves within-day clustering but not all multi-day dependence.
- The five families are not pooled. Matched controls use identical timestamps and opposite direction.
- BID-only historical results do not establish Pocket Option executable profitability.

## Reproducibility

- Machine-readable manifest: manifest.json
- Selected trade ledger: trades.csv
