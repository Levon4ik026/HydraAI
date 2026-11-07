import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from reproduce_m5_bb_williams_adx import Bar, run_trades


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


if __name__ == "__main__":
    unittest.main()
