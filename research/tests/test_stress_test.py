import unittest
from datetime import datetime, timedelta, timezone
from research.backtest_engine import Candle, backtest_signals
from research.stress_test import (REGIME_ELEVATED, REGIME_EXTREME, REGIME_NORMAL,
    REGIME_UNAVAILABLE, classify_volatility_regimes, shock_candles,
    summarize_by_signal_regime, summarize_event_window, next_candle_baseline_by_regime)

def make_candles(ranges, start=None):
    start = start or datetime(2026, 11, 1, tzinfo=timezone.utc)
    rows, price = [], 1.1
    for i, width in enumerate(ranges):
        op = price
        close = op + width * (0.2 if i % 2 == 0 else -0.2)
        rows.append(Candle(start + timedelta(minutes=i), op,
            max(op, close) + width*0.4, min(op, close) - width*0.4, close))
        price = close
    return rows

class StressTestDiagnostics(unittest.TestCase):
    def test_warmup_and_lagged_baseline(self):
        rows = classify_volatility_regimes(make_candles([.001]*5 + [.004]), lookback=5)
        self.assertEqual([x["regime"] for x in rows[:5]], [REGIME_UNAVAILABLE]*5)
        self.assertEqual(rows[5]["regime"], REGIME_EXTREME)
        self.assertAlmostEqual(rows[5]["baseline_median_tr"], .001)

    def test_normal_elevated_extreme(self):
        rows = classify_volatility_regimes(make_candles([.001]*5 + [.0012,.002,.004]), lookback=5)
        self.assertEqual(rows[5]["regime"], REGIME_NORMAL)
        self.assertEqual(rows[6]["regime"], REGIME_ELEVATED)
        self.assertEqual(rows[7]["regime"], REGIME_EXTREME)

    def test_future_data_cannot_change_past_regime(self):
        candles = make_candles([.001]*6)
        before = classify_volatility_regimes(candles, lookback=5)[5]
        extended = candles + make_candles([.02], candles[-1].timestamp + timedelta(minutes=1))
        after = classify_volatility_regimes(extended, lookback=5)[5]
        self.assertEqual(before, after)

    def test_shock_requires_extreme_range_and_body(self):
        candles = make_candles([.001]*5 + [.004])
        last = candles[-1]
        candles[-1] = Candle(last.timestamp, last.open, last.open + .004,
                             last.open - .001, last.open + .003)
        rows = classify_volatility_regimes(candles, lookback=5)
        self.assertEqual(len(shock_candles(rows)), 1)

    def test_grouping_by_signal_regime(self):
        candles = make_candles([.001]*5 + [.004,.001,.001])
        trades = backtest_signals(candles, {5:"CALL",6:"PUT"}, 1, allow_overlapping=True)
        grouped = summarize_by_signal_regime(trades, classify_volatility_regimes(candles, lookback=5))
        self.assertEqual(grouped[REGIME_EXTREME]["trades"], 1)
        self.assertEqual(grouped[REGIME_NORMAL]["trades"], 1)

    def test_event_window_excludes_late_settlement(self):
        candles = make_candles([.001]*5)
        trades = backtest_signals(candles, {0:"CALL",3:"CALL"}, 1, allow_overlapping=True)
        result = summarize_event_window(trades, candles[0].timestamp, candles[4].timestamp)
        self.assertEqual(result["trades"], 1)

    def test_gap_resets_regime_warmup_and_true_range(self):
        candles = make_candles([.001]*8)
        later = make_candles([.001]*8, candles[-1].timestamp + timedelta(minutes=2))
        combined = candles + later
        rows = classify_volatility_regimes(combined, lookback=5)
        self.assertEqual(rows[5]["regime"], REGIME_NORMAL)
        self.assertEqual(rows[6]["regime"], REGIME_UNAVAILABLE)
        self.assertEqual(rows[10]["regime"], REGIME_UNAVAILABLE)
        self.assertEqual(rows[11]["regime"], REGIME_NORMAL)

    def test_regime_matched_baseline_skips_gap_and_warmup(self):
        candles = make_candles([.001]*6)
        later = make_candles([.001]*6, candles[-1].timestamp + timedelta(minutes=2))
        candles += later
        regimes = classify_volatility_regimes(candles, lookback=5)
        baseline = next_candle_baseline_by_regime(candles, regimes)
        self.assertEqual(baseline[REGIME_NORMAL]["decisive"], 4)
        self.assertEqual(baseline[REGIME_NORMAL]["up"] + baseline[REGIME_NORMAL]["down"], 2)
        self.assertIsNotNone(baseline[REGIME_NORMAL]["call_win_rate"])


    def test_bad_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            classify_volatility_regimes(make_candles([.001]*5), lookback=1)
        with self.assertRaises(ValueError):
            classify_volatility_regimes(make_candles([.001]*5), elevated_ratio=3, extreme_ratio=2)

if __name__ == "__main__":
    unittest.main()
