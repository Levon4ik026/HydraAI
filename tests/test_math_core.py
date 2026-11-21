import unittest
from datetime import datetime, timedelta, timezone
from hydra_math_core import Candle, _rsi, backtest_non_overlapping, calculate_indicators, split_contiguous, summarize

UTC = timezone.utc
T0 = datetime(2026, 1, 1, tzinfo=UTC)

def candle(i, close, open_=None):
    o = close if open_ is None else open_
    return Candle(T0 + timedelta(minutes=i), o, max(o, close) + .0001, min(o, close) - .0001, close)

class MathCoreTests(unittest.TestCase):
    def test_gap_resets_indicator_warmup(self):
        data = [candle(i, 1.1 + i * .0001) for i in range(60)]
        data += [Candle(T0 + timedelta(minutes=90+i), 1.2, 1.2001, 1.1999, 1.2) for i in range(20)]
        self.assertEqual([len(s) for s in split_contiguous(data)], [60, 20])
        second = calculate_indicators(data, 3, 5, 3)[60:]
        self.assertTrue(all(x["ema_fast"] is None for x in second[:2]))
        self.assertTrue(all(x["ema_slow"] is None for x in second[:4]))
        self.assertTrue(all(x["rsi"] is None for x in second[:3]))

    def test_rsi_edge_cases(self):
        self.assertEqual(_rsi([1.0] * 20, 14)[14], 50.0)
        self.assertEqual(_rsi([float(i) for i in range(20)], 14)[14], 100.0)
        self.assertEqual(_rsi([20.0-i for i in range(20)], 14)[14], 0.0)

    def test_trade_cannot_cross_gap(self):
        rows = [{"timestamp": T0+timedelta(minutes=i), "open": 1.0, "close": 1.1, "signal": 1 if i == 1 else 0} for i in [0,1,2,4,5]]
        self.assertEqual(backtest_non_overlapping(rows, 2), [])

    def test_call_put_share_non_overlapping_scheduler(self):
        rows = [{"timestamp": T0+timedelta(minutes=i), "open": 1.0, "close": 1.1 if i%2 else .9,
                 "signal": 1 if i == 0 else (-1 if i == 1 else 0)} for i in range(5)]
        trades = backtest_non_overlapping(rows, 2)
        for a, b in zip(trades, trades[1:]):
            self.assertGreater(b.entry_time, a.exit_time)


    def test_new_signal_at_expiry_close_can_enter_next_candle(self):
        rows = [{"timestamp": T0+timedelta(minutes=i), "open": 1.0, "close": 1.1,
                 "signal": 1 if i in (0, 2) else 0} for i in range(5)]
        trades = backtest_non_overlapping(rows, 2)
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0].exit_time, trades[1].signal_time)
        self.assertGreater(trades[1].entry_time, trades[0].exit_time)

    def test_backtest_rejects_duplicate_or_reversed_timestamps(self):
        base = [
            {"timestamp": T0 + timedelta(minutes=i), "open": 1.0, "close": 1.1,
             "signal": 1 if i == 0 else 0}
            for i in range(4)
        ]
        duplicate = [dict(row) for row in base]
        duplicate[2]["timestamp"] = duplicate[1]["timestamp"]
        reversed_rows = [dict(row) for row in base]
        reversed_rows[2]["timestamp"] = T0 - timedelta(minutes=1)
        for malformed in (duplicate, reversed_rows):
            with self.subTest(rows=malformed):
                with self.assertRaisesRegex(ValueError, "strictly increasing"):
                    backtest_non_overlapping(malformed, 1)

    def test_backtest_rejects_nonfinite_or_nonpositive_prices(self):
        for bad in (float("nan"), float("inf"), 0.0, -1.0):
            rows = [
                {"timestamp": T0 + timedelta(minutes=i), "open": 1.0, "close": 1.1,
                 "signal": 1 if i == 0 else 0}
                for i in range(3)
            ]
            rows[1]["open"] = bad
            with self.subTest(price=bad):
                with self.assertRaisesRegex(ValueError, "open must be finite and positive"):
                    backtest_non_overlapping(rows, 1)

    def test_horizon_must_be_positive_integer(self):
        rows = [{"timestamp": T0 + timedelta(minutes=i), "open": 1.0, "close": 1.1,
                 "signal": 0} for i in range(3)]
        for horizon in (0, -1, 1.5, True):
            with self.subTest(horizon=horizon):
                with self.assertRaises(ValueError):
                    backtest_non_overlapping(rows, horizon)

    def test_actual_payout_override(self):
        rows = [{"timestamp": T0+timedelta(minutes=i), "open": 1.0, "close": 1.1, "signal": 1 if i == 0 else 0} for i in range(3)]
        entry = T0 + timedelta(minutes=1)
        trade = backtest_non_overlapping(rows, 1, .8, {entry: .94})[0]
        self.assertAlmostEqual(trade.profit_units, .94)
        self.assertAlmostEqual(trade.payout, .94)

    def test_draw_is_zero(self):
        rows = [{"timestamp": T0+timedelta(minutes=i), "open": 1.0, "close": 1.0, "signal": 1 if i == 0 else 0} for i in range(3)]
        trades = backtest_non_overlapping(rows, 1)
        self.assertEqual(summarize(trades)["draws"], 1)
        self.assertEqual(summarize(trades)["net_profit_units"], 0.0)

if __name__ == "__main__":
    unittest.main()
