import unittest
from research.signal_market_baseline import wilson, rate_text, outcome_counts, make_report

class SignalMarketBaselineTests(unittest.TestCase):
    def test_wilson_bounds(self):
        lo, hi = wilson(8, 10)
        self.assertLess(lo, 0.8)
        self.assertGreater(hi, 0.8)
        self.assertIsNone(wilson(0, 0)[0])

    def test_directional_outcomes(self):
        rows = [{"up": True, "down": False, "draw": False},
                {"up": False, "down": True, "draw": False},
                {"up": False, "down": False, "draw": True}]
        self.assertEqual(outcome_counts(rows, "CALL"), (1, 1, 1))
        self.assertEqual(outcome_counts(rows, "PUT"), (1, 1, 1))

    def test_rate_text_reports_interval(self):
        self.assertIn("[", rate_text(5, 10))
        self.assertEqual(rate_text(0, 0), "—")

if __name__ == "__main__":
    unittest.main()
