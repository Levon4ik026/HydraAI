# HydraAI — PUT-only strategy discovery, first screen (2026-11-07)

Branch: `hydra/stabilization`  
Payout: **92% only** (+0.92 win / -1.00 loss / 0 draw).  
Status: exploratory research only; no Desktop or production math-core changes.

## Objective

Search for a dedicated PUT strategy rather than forcing the CALL strategy to be symmetric. CALL remains frozen as a separate research control. Each candidate below generates PUT-only signals and uses its own sequential, non-overlapping trade scheduler.

## Data and execution convention

- Input: `eurusd_history_extended.csv`, 30,048 M1 rows.
- Range: 2026-10-07 04:31 UTC through 2026-10-28 01:19 UTC.
- Built 6,008 complete UTC-aligned M5 candles across 2 continuous segments.
- Incomplete M5 buckets are excluded; no trade crosses a data gap.
- Chronological 70/30 split; boundary 2026-10-21 19:05 UTC.
- Signal is known at M5 close; entry is next M5 open; settlement is that entry candle's close.
- Train/holdout membership is assigned by settlement timestamp.
- OHLC direction proxy only; no live quote, spread, payout-at-entry, or execution-latency simulation.

The sample is only about three weeks and overlaps prior October research. It is not an independent validation set.

## Candidate families screened

18 rule variants spanning:
- Bollinger upper-band re-entry + Williams %R, with ADX variants.
- RSI overbought fade.
- Stochastic bearish cross in a lower-price regime.
- EMA20 pullback under EMA50 with RSI confirmation.
- Donchian breakdown with DMI/ADX.
- MACD histogram zero-cross.
- CCI overbought fade.
- Bearish engulfing with EMA trend and ADX.
- ATR expansion / range breakdown.

14 candidates had at least 25 decisive training trades and were included in the ranked output. Candidates were ranked by training net only; holdout was displayed, not used for ranking.

## Main result: no robust PUT candidate yet

The highest training-ranked candidate was `STOCH_TREND:80`:
- Train: 79 decisive trades, 54.43% WR, +3.56 units.
- Holdout: 52 decisive trades, 42.31% WR, -9.76 units.

It failed to transfer to holdout.

The most interesting low-strength lead was `EMA_PULLBACK:20` with an ADX >=20 diagnostic filter:
- Train: 114 decisive trades, 52.63% WR, +1.20 units.
- Holdout: 43 decisive trades, 53.49% WR, +1.16 units.
- 95% Wilson intervals: train 43.53–61.56%; holdout 38.92–67.49%.

Both point estimates are only slightly above the 52.0833% break-even rate, and both confidence intervals include materially losing performance. Net gains are tiny. This is a lead for further diagnosis, not a candidate ready for use.

Other examples:
- `ATR_EXPANSION:20`: train -3.68, holdout -1.24 units.
- `DONCHIAN_BREAK:40`: train -11.16, holdout +1.04 units.
- `BEAR_ENGULF:15`: train -3.28, holdout -11.72 units.
- The tested BB/Williams PUT re-entry variant remained negative overall on this short sample.

## Regime diagnosis: EMA pullback may not be a conventional trend-following PUT

Across the full short sample, EMA pullback outcomes differed sharply by signal-time context:
- Bearish DMI: 167 decisive trades, 46.71% WR, -17.24 units.
- Bullish DMI or unavailable: 61 decisive trades, 63.93% WR, +13.88 units.
- Prior 3-bar momentum DOWN: 149 decisive trades, 44.97% WR, -20.36 units.
- Prior 3-bar momentum UP/FLAT: 79 decisive trades, 63.29% WR, +17.00 units.

This suggests that the better outcomes were not coming from ordinary bearish continuation. But the split-by-period diagnostics show why we must be cautious:
- Train, bullish-DMI + upward/flat M3: only 18 decisive trades, 77.78% WR, +8.88 units.
- Holdout, same bucket: only 4 decisive trades, 75.00% WR, +1.76 units.
- Train/holdout counts are far too small to establish a stable regime effect.

The ADX >=20 + bullish-DMI subset had 37 decisive train trades (67.57%) but only 6 decisive holdout trades (83.33%). The holdout count is especially too small to interpret. ADX >=20 + M3-up had 43 decisive train trades (69.77%) but only 17 decisive holdout trades (52.94%). These are exploratory slices with multiple comparisons, not selected filters.

## Reconcile with the earlier broad-screening PUT lead

The earlier broad report on `main` recorded a different PUT-only result for M5 Bollinger re-entry + Williams %R + ADX:
- Train: 909 trades, 54.83% WR, +46.96 units.
- Holdout: 376 trades, 53.83% WR, +12.24 units.

However, the same report states that this holdout edge weakened over time:
- June +5.08 units
- July +12.08
- August -1.12
- September -0.28
- October -0.04
- November -3.48

The raw 486,488-candle source CSV and exact original broad-screen implementation are not present in this branch's repository tree. The October short-sample re-test therefore cannot yet be claimed as an exact reproduction of the earlier broad result. The discrepancy remains unresolved and is now a priority research question.

## Decisions

1. Do not promote any new PUT candidate into HydraAI Desktop.
2. Do not alter the frozen CALL research candidate.
3. Do not encode DMI/momentum filters in production.
4. Preserve 92% payout as the sole tested payout convention.
5. Next research priority: reconstruct the exact original broad M5 PUT rule and explain its deterioration by month/regime. Then expand candidate families only where the evidence indicates a different mechanism.
6. Before any combined CALL/PUT engine is considered, test both frozen directional engines together with one shared scheduler and a conflict/WAIT policy on a fresh, untouched sample.

## Reproducibility

Implementation: `research/screen_put_strategies.py`  
Workflow: `.github/workflows/math-core-tests.yml`  
Latest successful GitHub Actions run: #21, run ID `42371731268`, commit `238b138e1fa3d67fdb997cb6b6aed6d72342b697`. Unit tests, frozen M5 report, and PUT screen all completed successfully. Artifact: `put-strategy-screen`.

This CI success verifies that the research code executes; it does not validate a trading edge.
