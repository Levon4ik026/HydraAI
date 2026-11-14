import math
import unittest

from research.lee_mykland_jump import detect_jumps, _threshold


class LeeMyklandTests(unittest.TestCase):
    def test_threshold_increases_with_confidence(self):
        self.assertLess(_threshold(10000, 0.90), _threshold(10000, 0.95))
        self.assertLess(_threshold(10000, 0.95), _threshold(10000, 0.99))

    def test_detects_large_positive_and_negative_shocks(self):
        closes = [1.0]
        # Stable small returns build a non-zero local bipower variance.
        for i in range(80):
            closes.append(closes[-1] * math.exp(0.0001 if i % 2 == 0 else -0.0001))
        closes.append(closes[-1] * math.exp(0.02))
        for i in range(10):
            closes.append(closes[-1] * math.exp(0.0001 if i % 2 == 0 else -0.0001))
        closes.append(closes[-1] * math.exp(-0.02))
        jumps = detect_jumps(closes, k=16, confidence=0.99)
        directions = [j.direction for j in jumps]
        self.assertIn("CALL", directions)
        self.assertIn("PUT", directions)

    def test_invalid_prices_rejected(self):
        with self.assertRaises(ValueError):
            detect_jumps([1.0, 1.0, 0.0, 1.0, 1.0], k=4, confidence=0.95)

    def test_no_future_return_in_local_volatility(self):
        # The same pre-shock history must produce the same sigma/threshold
        # for the event return regardless of the post-event tail.
        base = [1.0]
        for i in range(40):
            base.append(base[-1] * math.exp(0.0001 if i % 2 == 0 else -0.0001))
        event = base[-1] * math.exp(0.02)
        a = detect_jumps(base + [event], k=16, confidence=0.95, threshold_n=1000)
        b = detect_jumps(base + [event] + [event * 1.0001] * 20,
                         k=16, confidence=0.95, threshold_n=1000)
        ja = next(j for j in a if j.index == len(base))
        jb = next(j for j in b if j.index == len(base))
        self.assertAlmostEqual(ja.local_sigma, jb.local_sigma)
        self.assertAlmostEqual(ja.l_statistic, jb.l_statistic)


if __name__ == "__main__":
    unittest.main()
