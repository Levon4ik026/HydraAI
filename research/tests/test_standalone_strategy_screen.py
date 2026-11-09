import sys
import unittest
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1]
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from standalone_strategy_screen import summarize, wilson_interval


class StandaloneStrategyMetricsTests(unittest.TestCase):
    def test_draw_is_zero_net_and_excluded_from_decisive_wr(self):
        result = summarize(["W", "L", "D"])
        self.assertEqual((result["n"], result["w"], result["l"], result["d"]), (3, 1, 1, 1))
        self.assertAlmostEqual(result["wr"], 50.0)
        self.assertAlmostEqual(result["win_all"], 100.0 / 3.0)
        self.assertAlmostEqual(result["net"], -0.08)
        self.assertAlmostEqual(result["roi"], -0.08 / 3.0 * 100.0)
        self.assertAlmostEqual(result["pf"], 0.92)
        self.assertAlmostEqual(result["max_dd"], 1.0)
        self.assertEqual(result["max_losing_streak"], 1)
        self.assertIsNotNone(result["wilson"])

    def test_drawdown_and_losing_streak_follow_chronological_order(self):
        result = summarize(["W", "L", "L", "W", "L"])
        self.assertAlmostEqual(result["max_dd"], 2.08)
        self.assertEqual(result["max_losing_streak"], 2)
        self.assertAlmostEqual(result["net"], -1.16)

    def test_wilson_interval_uses_decisive_outcomes_only(self):
        low, high = wilson_interval(1, 2)
        self.assertAlmostEqual(low, 9.45, places=1)
        self.assertAlmostEqual(high, 90.55, places=1)

    def test_no_decisive_outcomes_has_no_win_rate_interval(self):
        result = summarize(["D", "D"])
        self.assertIsNone(result["wr"])
        self.assertIsNone(result["wilson"])
        self.assertEqual(result["net"], 0.0)
        self.assertEqual(result["max_dd"], 0.0)
        self.assertEqual(result["max_losing_streak"], 0)


if __name__ == "__main__":
    unittest.main()
