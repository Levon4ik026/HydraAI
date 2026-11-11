import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1]
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from standalone_strategy_screen import summarize, wilson_interval, split_dates, split_mode


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


    def test_split_dates_are_frozen_when_history_is_extended(self):
        days = [
            date(2024, 1, 2),
            date(2025, 9, 16),
            date(2025, 9, 17),
            date(2026, 4, 13),
            date(2026, 4, 14),
            date(2026, 11, 11),
        ]
        segment = [
            SimpleNamespace(timestamp=datetime(day.year, day.month, day.day, tzinfo=timezone.utc))
            for day in days
        ]
        self.assertEqual(
            split_dates([segment]),
            (date(2025, 9, 17), date(2026, 4, 14)),
        )

    def test_short_history_uses_relative_chronological_fallback(self):
        days = [date(2026, 10, 1) + timedelta(days=i) for i in range(10)]
        segment = [
            SimpleNamespace(timestamp=datetime(day.year, day.month, day.day, tzinfo=timezone.utc))
            for day in days
        ]
        d1, d2 = split_dates([segment])
        self.assertEqual((d1, d2), (days[6], days[8]))
        self.assertEqual(
            split_mode(d1, d2),
            "relative 60/80% fallback for shorter history",
        )

    def test_no_decisive_outcomes_has_no_win_rate_interval(self):
        result = summarize(["D", "D"])
        self.assertIsNone(result["wr"])
        self.assertIsNone(result["wilson"])
        self.assertEqual(result["net"], 0.0)
        self.assertEqual(result["max_dd"], 0.0)
        self.assertEqual(result["max_losing_streak"], 0)


if __name__ == "__main__":
    unittest.main()
