import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixing_daily_reversal_screen import (
    Bar, LONDON, BERLIN, local_time, minute_window, outcome,
    period_quality, parse_timestamp, split_records, wilson,
)


class FixingDailyReversalTests(unittest.TestCase):
    def test_millisecond_timestamp_parses_to_utc_minute(self):
        row = {"timestamp": "1796033700000"}
        ts = parse_timestamp(row, ["timestamp"])
        self.assertEqual(ts.tzinfo, timezone.utc)
        self.assertEqual(ts.second, 0)

    def test_dst_aware_fix_times(self):
        summer_berlin = local_time(datetime(2026, 3, 30).date(), 14, 15, BERLIN)
        winter_berlin = local_time(datetime(2026, 11, 2).date(), 14, 15, BERLIN)
        summer_london = local_time(datetime(2026, 3, 30).date(), 16, 0, LONDON)
        winter_london = local_time(datetime(2026, 11, 2).date(), 16, 0, LONDON)
        self.assertEqual((summer_berlin.hour, summer_berlin.minute), (12, 15))
        self.assertEqual((winter_berlin.hour, winter_berlin.minute), (13, 15))
        self.assertEqual((summer_london.hour, summer_london.minute), (15, 0))
        self.assertEqual((winter_london.hour, winter_london.minute), (16, 0))

    def test_minute_window_rejects_missing_minute(self):
        start = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        bars = {
            start: Bar(start, 1.1, 1.1, 1.1, 1.1),
            start + timedelta(minutes=2): Bar(start + timedelta(minutes=2), 1.1, 1.1, 1.1, 1.1),
        }
        self.assertIsNone(minute_window(bars, start, 3))

    def test_call_put_outcomes_are_exact_inverses(self):
        entry = Bar(datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc), 1.1, 1.1, 1.1, 1.1)
        settle = Bar(datetime(2026, 1, 5, 12, 59, tzinfo=timezone.utc), 1.101, 1.101, 1.101, 1.101)
        self.assertEqual(outcome(entry, settle, "CALL"), "W")
        self.assertEqual(outcome(entry, settle, "PUT"), "L")

    def test_period_quality_allows_one_missing_minute_only(self):
        start = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        bars = {}
        for i in range(100):
            if i == 50:
                continue
            ts = start + timedelta(minutes=i)
            bars[ts] = Bar(ts, 1.1, 1.1, 1.1, 1.1)
        result = period_quality(bars, start, start + timedelta(minutes=100))
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["coverage"], 0.99)

    def test_wilson_interval_contains_observed_rate(self):
        low, high = wilson(70, 100)
        self.assertLess(low, 70.0)
        self.assertGreater(high, 70.0)


if __name__ == "__main__":
    unittest.main()
