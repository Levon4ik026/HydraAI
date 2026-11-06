# HydraAI — Indicator screening (2026-11-06)

## Dataset and method
- Input: `eurusd_research_clean.csv`, 486,488 one-minute OHLC candles.
- Range: 2025-07-21 15:11 UTC to 2026-11-05 16:08 UTC.
- Validation: 0 invalid OHLC rows, 0 duplicate timestamps; 68 continuous segments separated by 67 gaps. Largest gap: 2,951 minutes.
- Timeframes: M1, M2, M3, M5. Higher-timeframe candles are UTC-aligned; incomplete buckets are excluded.
- Chronological split: first 70% for screening, last 30% holdout. Boundary: 2026-06-17 04:44 UTC.
- Signal after candle close; entry at next candle open; settlement at next candle close (one bar expiry).
- Payout model: +0.92 per win, -1 per loss, 0 for draw. No spread/slippage/quote-latency model.
- Trades are sequential; no overlapping positions. The split is assigned by settlement candle timestamp.

## Tested combinations
1. Donchian breakout + EMA trend alignment + range/ATR expansion.
2. Keltner channel breakout + EMA trend alignment.
3. Supertrend direction flip + RSI confirmation.
4. Bollinger re-entry + Williams %R + ADX regime filter.
5. Ichimoku cloud breakout + Tenkan/Kijun alignment.
6. EMA trend pullback + candle rejection + RSI regime.

## Main finding
None of the 24 complete strategy/timeframe combinations produced positive net profit on the holdout. Best aggregate holdout result was M2 Ichimoku: 2,321 trades, 50.999% win rate excluding draws, net -45.84 units, ROI -1.98%.

One directional subset was positive in both periods: M5 Bollinger re-entry + Williams %R + ADX, PUT signals only:
- Train: 909 trades, 54.83% win rate, +46.96 units, +5.17% net per trade.
- Holdout: 376 trades, 53.83% win rate, +12.24 units, +3.26% net per trade, max drawdown 13.96 units.
- CALL side was negative on both periods; combining CALL and PUT made the full strategy negative on holdout (-18.08 units).

This is a research lead, not a validated production strategy. Holdout subperiod results weaken materially after July 2026: June +5.08, July +12.08, August -1.12, September -0.28, October -0.04, November -3.48 units. The positive result is concentrated early in the holdout. The candidate needs a fresh untouched forward test and robustness checks before any use.

## Important limitations
- This was a first-pass fixed-rule screening, not an exhaustive search of all indicators or parameter combinations.
- Binary outcome is approximated from OHLC: next bar open to next bar close. Actual Pocket Option quote, execution timing, payout variation, and platform settlement may differ.
- The CSV has large historical gaps; indicators are calculated independently within continuous segments and trades do not bridge gaps.
- No strategy is approved for live trading. HydraAI's existing strategy and manual-only workflow were not changed.

See `indicator_screening_summary.csv` for all 24 train/holdout rows.
