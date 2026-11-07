# Audit of the original M5 PUT screening artifacts (2026-11-07)

Branch: `hydra/stabilization`  
Scope: source-code provenance and timestamp/outcome alignment. No production changes.

## What was recovered

The original 2026-11-06 screening artifacts were recovered from the user's Library and checked against GitHub commit history:

- `hydra_indicator_screening_summary.csv` — 24 aggregate strategy/timeframe rows.
- `hydra_indicator_screening_directions.csv` — 48 directional rows.
- `hydra_m5_put_holdout_trades.csv` — 376 PUT holdout trades.
- `eurusd_research_clean.csv` — 486,488 M1 OHLC rows.

The direction summary confirms the exact historical result:
- M5 BB Re-entry + WilliamsR + ADX, PUT train: 909 trades, 54.831461% WR, +46.96 units.
- PUT holdout: 376 trades, 53.825137% WR, +12.24 units.
- Corresponding CALL side: train 960 trades, 46.474359% WR, -100.80 units; holdout 394 trades, 47.860963% WR, -30.32 units.

The 376-row trade log contains 197 wins, 169 losses, and 10 draws. Its saved PnL agrees with the direction of the matching UTC-aligned M5 entry candle (entry candle close versus open). The CSV time field labels the final M1 minute of the five-minute entry candle; e.g. 07:14 corresponds to the 07:10–07:14 entry candle, with the preceding signal candle 07:05–07:09.

## Provenance finding: the original implementation is absent

The GitHub commits that introduced the original report and screening summary contain only:
- `research/indicator_screening_2026-11-06.md`
- `research/indicator_screening_summary.csv`
- `research/indicator_screening_directions.csv`

They do not contain the executable screening script, parameter configuration, or serialized signal rows for the training sample. A scan of the recovered `HYDRA_COMPLETE_SOURCE(1).zip` likewise found no original research screening script or Bollinger/Williams/ADX implementation. The current branch's `reproduce_m5_bb_williams_adx.py` is a later, explicitly specified reproduction attempt; it is not the original broad-screen program.

Therefore, the original PUT edge cannot yet be reproduced bit-for-bit from repository history alone. The missing details include the exact band and Williams conditions, ADX threshold/initialization, M5 construction and timestamp convention, indicator warm-up behavior, and candidate scheduler ordering.

## Independent reconstruction probe

A first parameter probe over UTC-aligned complete M5 bars tested common BB/Williams variants (BB lengths 14/20/24, deviations 1.5/2/2.5, Williams lengths 10/14/20, close-cross or wick-cross of the upper band, Williams cross or state below -20). None matched more than 192 of the 376 historical signal timestamps (51.1% recall); most generated thousands of extra signals. This confirms that guessing the conventional textbook rule is not enough to recover the original signal selector.

The probe is explicitly diagnostic and was not used to choose or modify a strategy.

## Important boundary detail

The original 2026-11-06 report states a chronological 70/30 boundary of 2026-06-17 04:44 UTC. A later M5-only split based on the count of complete M5 bars lands at 05:00 UTC. For faithful reconstruction, use the original stated timestamp boundary (04:44 UTC) for train/holdout assignment rather than silently substituting a newly computed M5-count boundary.

## Next required recovery path

1. Locate the original local research notebook/script or shell history used to create the three CSV artifacts; it is not present in the recovered Desktop source archive or the two GitHub artifact commits.
2. If the original script cannot be recovered, reconstruct the selector from all 909 train plus 376 holdout signal timestamps—not just the holdout—and treat the reconstruction as a new hypothesis until it matches the saved timestamp set without fitting on holdout alone.
3. Validate exact match on train and holdout separately, then independently recompute all outcomes from raw OHLC.
4. Only after timestamp-level parity is achieved should monthly edge-decay, session, volatility, and regime diagnostics be attributed to the original selector.

No production math core, Desktop code, branch main, or live behavior was changed.
