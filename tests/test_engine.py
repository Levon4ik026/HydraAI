import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hydra_demo.engine import Candle, aggregate_m5, check_feed, DemoExecutionGate, ema, rsi


class EngineTests(unittest.TestCase):
    def make_candles(self, n=65):
        start = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
        return [Candle(start + timedelta(minutes=i), 1.1+i*0.00001,
                       1.1002+i*0.00001, 1.0998+i*0.00001,
                       1.1001+i*0.00001) for i in range(n)]

    def test_feed_continuity(self):
        cs = self.make_candles()
        now = cs[-1].timestamp + timedelta(seconds=20)
        self.assertTrue(check_feed(cs, now=now).ok)

    def test_feed_gap_rejected(self):
        cs = self.make_candles()
        cs[-2] = Candle(cs[-2].timestamp - timedelta(minutes=2), cs[-2].open,
                        cs[-2].high, cs[-2].low, cs[-2].close)
        cs.sort(key=lambda x: x.timestamp)
        self.assertFalse(check_feed(cs, now=cs[-1].timestamp + timedelta(seconds=5)).ok)

    def test_m5_requires_complete_groups(self):
        cs = self.make_candles(12)
        m5 = aggregate_m5(cs)
        self.assertEqual(len(m5), 2)
        self.assertEqual(m5[0].open, cs[0].open)
        self.assertEqual(m5[0].close, cs[4].close)

    def test_indicators(self):
        vals = [float(i) for i in range(30)]
        self.assertIsNotNone(ema(vals, 20)[-1])
        self.assertGreater(rsi(vals)[-1], 99)

    def test_execution_fails_closed_by_default(self):
        gate = DemoExecutionGate()
        ok, reason = gate.can_submit(feed_ok=True, payout=0.95,
                                     open_positions=0, daily_loss_units=0)
        self.assertFalse(ok)
        self.assertIn("not verified", reason)

    def test_execution_risk_limits(self):
        gate = DemoExecutionGate(broker_adapter_verified=True)
        self.assertTrue(gate.can_submit(feed_ok=True, payout=0.95,
                                        open_positions=0, daily_loss_units=0)[0])
        self.assertFalse(gate.can_submit(feed_ok=False, payout=0.95,
                                         open_positions=0, daily_loss_units=0)[0])
        self.assertFalse(gate.can_submit(feed_ok=True, payout=0.91,
                                         open_positions=0, daily_loss_units=0)[0])
        self.assertFalse(gate.can_submit(feed_ok=True, payout=0.95,
                                         open_positions=1, daily_loss_units=0)[0])


if __name__ == "__main__":
    unittest.main()
