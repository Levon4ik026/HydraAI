import unittest
from datetime import datetime, timedelta, timezone

from research.backtest_engine import (
    Candle, backtest_signals, chronological_partitions, summarize_trades,
    trades_in_window, validate_candles, walk_forward_windows,
)


def series(closes, start=None):
    start = start or datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
    result = []
    previous = closes[0]
    for i, close in enumerate(closes):
        stamp = start + timedelta(minutes=i)
        open_price = previous
        result.append(Candle(stamp, open_price, max(open_price, close) + 0.001,
                             min(open_price, close) - 0.001, close))
        previous = close
    return result


class BacktestEngineTests(unittest.TestCase):
    def test_next_candle_entry_and_one_minute_expiry(self):
        candles = series([1.100, 1.101, 1.102])
        trades = backtest_signals(candles, {0: "CALL"}, 1, payout=0.92)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_price, candles[1].open)
        self.assertEqual(trades[0].exit_price, candles[1].close)
        self.assertEqual(trades[0].outcome, "WIN")
        self.assertEqual(trades[0].profit_units, 0.92)

    def test_put_loss_and_variable_payout(self):
        candles = series([1.100, 1.101, 1.102, 1.099])
        trades = backtest_signals(candles, {0: "PUT", 1: "CALL"}, 2,
                                  payout={0: 0.92, 1: 0.85}, allow_overlapping=True)
        self.assertEqual(trades[0].outcome, "LOSS")
        self.assertEqual(trades[0].profit_units, -1.0)
        self.assertEqual(trades[0].payout, 0.92)

    def test_gap_blocks_trade(self):
        candles = series([1.1, 1.101, 1.102, 1.103])
        candles[2] = Candle(candles[2].timestamp + timedelta(minutes=1),
                            candles[2].open, candles[2].high,
                            candles[2].low, candles[2].close)
        candles[3] = Candle(candles[3].timestamp + timedelta(minutes=1),
                            candles[3].open, candles[3].high,
                            candles[3].low, candles[3].close)
        validate_candles(candles)
        trades = backtest_signals(candles, {0: "CALL"}, 2)
        self.assertEqual(trades, [])

    def test_non_overlapping_signals(self):
        candles = series([1.100, 1.101, 1.102, 1.103, 1.104, 1.105])
        signals = {0: "CALL", 1: "CALL", 2: "CALL"}
        trades = backtest_signals(candles, signals, 2)
        self.assertEqual([t.signal_time for t in trades],
                         [candles[0].timestamp, candles[2].timestamp])

    def test_draw_and_summary_at_92_percent(self):
        candles = series([1.1, 1.1, 1.101, 1.100])
        trades = backtest_signals(candles, {0: "CALL", 1: "CALL"}, 1,
                                  payout=0.92, allow_overlapping=True)
        self.assertEqual(trades[0].outcome, "DRAW")
        stats = summarize_trades(trades)
        self.assertEqual(stats["draws"], 1)
        self.assertEqual(stats["break_even_win_rate_pct"], 52.0833)

    def test_chronological_partitions_are_disjoint(self):
        candles = series([1.1 + i * 0.001 for i in range(10)])
        parts = chronological_partitions(candles)
        self.assertEqual(parts, {"train": (0, 6), "validation": (6, 8), "holdout": (8, 10)})

    def test_trade_must_settle_inside_window(self):
        candles = series([1.1 + i * 0.001 for i in range(6)])
        trades = backtest_signals(candles, {0: "CALL", 3: "CALL"}, 2, allow_overlapping=True)
        start, end = candles[0].timestamp, candles[4].timestamp + timedelta(minutes=1)
        kept = trades_in_window(trades, start, end)
        self.assertEqual(len(kept), 1)

    def test_walk_forward_windows_expand_training_only(self):
        windows = walk_forward_windows(12, train_size=6, validation_size=3, step_size=2)
        self.assertEqual(windows, [
            {"train": (0, 6), "validation": (6, 9)},
            {"train": (0, 8), "validation": (8, 11)},
        ])

    def test_signal_at_expiry_close_can_enter_next_candle(self):
        candles = series([1.100, 1.101, 1.102, 1.103, 1.104, 1.105])
        trades = backtest_signals(candles, {0: "CALL", 1: "PUT", 2: "CALL"}, 2)
        self.assertEqual([t.signal_time for t in trades],
                         [candles[0].timestamp, candles[2].timestamp])
        self.assertEqual(trades[0].settlement_time, trades[1].entry_time)

    def test_draw_epsilon_must_be_finite_and_non_negative(self):
        candles = series([1.100, 1.101, 1.102])
        for epsilon in (float("nan"), float("inf"), float("-inf"), -1e-9):
            with self.subTest(epsilon=epsilon):
                with self.assertRaises(ValueError):
                    backtest_signals(candles, {0: "CALL"}, 1, draw_epsilon=epsilon)

    def test_duplicate_timestamps_rejected(self):
        candles = series([1.1, 1.101, 1.102])
        candles[2] = Candle(candles[1].timestamp, candles[2].open, candles[2].high,
                            candles[2].low, candles[2].close)
        with self.assertRaises(ValueError):
            validate_candles(candles)


if __name__ == "__main__":
    unittest.main()
