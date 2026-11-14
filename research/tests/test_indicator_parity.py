import math
import unittest
from datetime import datetime, timedelta, timezone

from research.frozen_put_candidate import wilder_atr
from research.reproduce_m5_bb_williams_adx import Bar, indicators
from research.screen_put_strategies import atr


class IndicatorParityTests(unittest.TestCase):
    def synthetic_bars(self, count=120):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        bars = []
        previous = 1.10
        for i in range(count):
            drift = 0.00013 * math.sin(i * 0.31) + 0.000025 * (1 if i % 7 < 4 else -1)
            close = previous + drift
            open_ = previous + 0.00002 * math.cos(i * 0.17)
            high = max(open_, close) + 0.00011 + (i % 5) * 0.000007
            low = min(open_, close) - 0.00009 - (i % 3) * 0.000009
            bars.append(Bar(start + timedelta(minutes=5 * i), open_, high, low, close))
            previous = close
        return bars

    def test_screen_atr_and_frozen_candidate_atr_are_identical(self):
        bars = self.synthetic_bars()
        screen = atr(bars, 14)
        frozen = wilder_atr(bars, 14)
        self.assertEqual(len(screen), len(frozen))
        for index, (left, right) in enumerate(zip(screen, frozen)):
            if left is None or right is None:
                self.assertIsNone(left)
                self.assertIsNone(right)
            else:
                self.assertAlmostEqual(left, right, places=15, msg=f"ATR mismatch at {index}")

    def test_bollinger_uses_population_standard_deviation(self):
        bars = self.synthetic_bars()
        values = indicators(bars)
        i = 30
        closes = [b.close for b in bars[i - 19:i + 1]]
        mean = sum(closes) / 20
        population_sd = math.sqrt(sum((x - mean) ** 2 for x in closes) / 20)
        sample_sd = math.sqrt(sum((x - mean) ** 2 for x in closes) / 19)
        self.assertAlmostEqual(values[i]["upper"], mean + 2 * population_sd, places=14)
        self.assertGreater(mean + 2 * sample_sd, values[i]["upper"])

    def test_williams_r_matches_rolling_high_low_formula(self):
        bars = self.synthetic_bars()
        values = indicators(bars)
        i = 40
        window = bars[i - 13:i + 1]
        highest = max(b.high for b in window)
        lowest = min(b.low for b in window)
        expected = -100 * (highest - bars[i].close) / (highest - lowest)
        self.assertAlmostEqual(values[i]["willr"], expected, places=14)

    def test_adx_is_unavailable_until_fourteen_valid_dx_values(self):
        bars = self.synthetic_bars(30)
        values = indicators(bars)
        # First DX is at index 14; the 14-value ADX seed is at index 27.
        self.assertTrue(all(values[i]["adx"] is None for i in range(27)))
        self.assertIsNotNone(values[27]["adx"])


if __name__ == "__main__":
    unittest.main()
