from datetime import datetime, timedelta, timezone
import unittest

from hydra_demo.engine import Candle, candidate_signals


class CandidateStrategyTests(unittest.TestCase):
    def test_cand012_bearish_cross_uses_approved_inverse_call(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        m1 = []
        previous = 1.1000
        closes = []
        for i in range(80):
            if i < 55:
                target = 1.1000 + i * 0.00005
            else:
                target = 1.1000 + 54 * 0.00005 - (i - 54) * 0.00015
            closes.append(target)

        for block, target in enumerate(closes):
            block_open = previous
            for minute in range(5):
                next_price = block_open + (target - block_open) * (minute + 1) / 5
                candle_open = block_open + (target - block_open) * minute / 5
                ts = start + timedelta(minutes=block * 5 + minute)
                m1.append(Candle(
                    timestamp=ts,
                    open=candle_open,
                    high=max(candle_open, next_price) + 0.00001,
                    low=min(candle_open, next_price) - 0.00001,
                    close=next_price,
                ))
            previous = target

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-012"]
        self.assertTrue(signals, "synthetic trend reversal should produce a CAND-012 signal")
        self.assertTrue(all(s.direction == "PUT" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 5 for s in signals))


if __name__ == "__main__":
    unittest.main()
