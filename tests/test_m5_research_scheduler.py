import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from reproduce_m5_bb_williams_adx import Bar, indicators, run_trades, summary, wilson_interval


UTC = timezone.utc
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def row(index, signal=0, segment_id=0):
    ts = T0 + timedelta(minutes=5 * index)
    bar = Bar(ts, 1.0, 1.1, 0.9, 1.05)
    return {"bar": bar, "signal": signal, "adx": 20.0, "segment_id": segment_id}


class M5ResearchSchedulerTests(unittest.TestCase):
    def test_signal_at_expiry_close_can_enter_next_candle(self):
        rows = [row(0, 1), row(1, 1), row(2), row(3)]
        trades = run_trades(rows, 15)
        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]["entry_time"], T0 + timedelta(minutes=5))
        self.assertEqual(trades[1]["entry_time"], T0 + timedelta(minutes=10))

    def test_trade_cannot_cross_segment_boundary(self):
        rows = [row(0, 1, 0), row(1, 0, 1), row(2, 0, 1)]
        self.assertEqual(run_trades(rows, 15), [])

    def test_trade_cannot_cross_missing_m5_bucket(self):
        rows = [row(0, 1, 0), row(2, 0, 0), row(3, 0, 0)]
        self.assertEqual(run_trades(rows, 15), [])

    def test_summary_reports_confidence_interval_and_drawdown(self):
        trades = [
            {"outcome": "WIN", "profit": 0.92},
            {"outcome": "LOSS", "profit": -1.0},
            {"outcome": "WIN", "profit": 0.92},
        ]
        result = summary(trades)
        self.assertEqual(result["trades"], 3)
        self.assertEqual(result["decisive"], 3)
        self.assertEqual(result["net_92"], 0.84)
        self.assertEqual(result["max_drawdown_units"], 1.0)
        self.assertIsNotNone(result["wilson_95_pct"])

    def test_wilson_interval_is_none_without_decisive_trades(self):
        self.assertIsNone(wilson_interval(0, 0))

    def test_dmi_directional_components_are_exposed(self):
        rising = [
            Bar(T0 + timedelta(minutes=5 * i),
                1.0 + i * 0.001,
                1.01 + i * 0.001,
                0.995 + i * 0.001,
                1.005 + i * 0.001)
            for i in range(40)
        ]
        result = indicators(rising)
        valid = [x for x in result if x["plus_di"] is not None and x["minus_di"] is not None]
        self.assertTrue(valid)
        self.assertGreater(valid[-1]["plus_di"], valid[-1]["minus_di"])
        self.assertIsNotNone(valid[-1]["adx"])


if __name__ == "__main__":
    unittest.main()
