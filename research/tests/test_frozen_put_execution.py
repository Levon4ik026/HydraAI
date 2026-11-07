import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from research.frozen_put_candidate import build_candidate
from research.reproduce_m5_bb_williams_adx import Bar


class FrozenPutExecutionTests(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 7, 13, 0, tzinfo=timezone.utc)

    def bars(self, next_open=10.0, next_close=9.0, next_offset=5):
        closes = [8.0, 8.2, 8.4, 9.0]
        result = []
        for i, close in enumerate(closes):
            result.append(Bar(
                self.start + timedelta(minutes=5 * i),
                close - 0.02, close + 0.05, close - 0.05, close,
            ))
        result.append(Bar(
            self.start + timedelta(minutes=15 + next_offset),
            next_open, max(next_open, next_close) + 0.05,
            min(next_open, next_close) - 0.05, next_close,
        ))
        return result

    def mocked_indicators(self, bars):
        values = [{"upper": 100.0, "willr": -50.0, "adx": 20.0}
                  for _ in bars]
        # At i=3: previous close is above its upper band, current close
        # re-enters below the upper band, and Williams %R crosses below -20.
        values[2] = {"upper": 8.4, "willr": -15.0, "adx": 20.0}
        values[3] = {"upper": 9.1, "willr": -25.0, "adx": 20.0}
        return values

    def run_candidate(self, bars):
        atr_values = [None, None, None, 0.01, None]
        with patch("research.frozen_put_candidate.indicators",
                   side_effect=self.mocked_indicators), \
             patch("research.frozen_put_candidate.wilder_atr",
                   return_value=atr_values):
            return build_candidate([bars])

    def test_signal_time_and_entry_expiry_are_next_m5_candle(self):
        bars = self.bars()
        trades = self.run_candidate(bars)
        self.assertEqual(len(trades), 1)
        trade = trades[0]
        self.assertEqual(trade["signal_time"], bars[3].timestamp)
        self.assertEqual(trade["entry_time"], bars[4].timestamp)
        self.assertEqual(trade["settlement_time"], bars[4].timestamp + timedelta(minutes=5))
        self.assertEqual(trade["outcome"], "WIN")
        self.assertAlmostEqual(trade["profit"], 0.92)

    def test_future_entry_candle_changes_outcome_not_signal_or_entry_time(self):
        winning = self.run_candidate(self.bars(next_open=10.0, next_close=9.0))
        losing = self.run_candidate(self.bars(next_open=10.0, next_close=11.0))
        self.assertEqual(len(winning), 1)
        self.assertEqual(len(losing), 1)
        self.assertEqual(winning[0]["signal_time"], losing[0]["signal_time"])
        self.assertEqual(winning[0]["entry_time"], losing[0]["entry_time"])
        self.assertEqual(winning[0]["outcome"], "WIN")
        self.assertEqual(losing[0]["outcome"], "LOSS")
        self.assertEqual(winning[0]["profit"], 0.92)
        self.assertEqual(losing[0]["profit"], -1.0)

    def test_nonconsecutive_next_candle_is_rejected(self):
        trades = self.run_candidate(self.bars(next_offset=6))
        self.assertEqual(trades, [])


if __name__ == "__main__":
    unittest.main()
