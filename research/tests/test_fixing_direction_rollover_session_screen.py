import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fixing_daily_reversal_screen import Bar, BERLIN, NY, local_time, period_quality
from fixing_direction_rollover_session_screen import make_trade, fixing_events


class DirectFixingRolloverTests(unittest.TestCase):
    def test_tokyo_and_europe_fix_times_are_dst_aware(self):
        summer = local_time(datetime(2026, 3, 30).date(), 14, 15, BERLIN)
        winter = local_time(datetime(2026, 11, 2).date(), 14, 15, BERLIN)
        self.assertEqual((summer.hour, summer.minute), (12, 15))
        self.assertEqual((winter.hour, winter.minute), (13, 15))

    def test_rollover_excluded_daily_session_is_complete(self):
        start = local_time(datetime(2026, 1, 5).date(), 18, 0, NY)
        end = local_time(datetime(2026, 1, 6).date(), 17, 0, NY)
        by_ts = {}
        for i in range(int((end-start).total_seconds()//60)):
            ts = start + timedelta(minutes=i)
            by_ts[ts] = Bar(ts, 1.1, 1.1, 1.1, 1.1)
        result = period_quality(by_ts, start, end, min_coverage=0.99, max_gap=5)
        self.assertIsNotNone(result)
        self.assertEqual(result["expected_minutes"], 1380)

    def test_weekly_quality_allows_expected_daily_rollover_gaps(self):
        start = datetime(2026, 1, 4, 18, 0, tzinfo=timezone.utc)
        end = start + timedelta(minutes=2000)
        by_ts = {}
        for i in range(2000):
            if 800 <= i < 860:
                continue
            ts = start + timedelta(minutes=i)
            by_ts[ts] = Bar(ts, 1.1, 1.1, 1.1, 1.1)
        result = period_quality(by_ts, start, end, min_coverage=0.95, max_gap=65)
        self.assertIsNotNone(result)
        self.assertEqual(result["largest_gap"], 60)

    def test_expiry_uses_close_of_last_included_m1_bar(self):
        start = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
        by_ts = {}
        for i in range(5):
            ts = start + timedelta(minutes=i)
            px = 1.1 + i * 0.0001
            by_ts[ts] = Bar(ts, px, px, px, px)
        trade = make_trade("X", start, start, by_ts, "CALL", -0.001, "test", 5)
        self.assertEqual(trade["outcome"], "W")
        self.assertEqual(trade["exit_price"], by_ts[start + timedelta(minutes=4)].close)
        self.assertEqual(trade["settle_time"], start + timedelta(minutes=5))

    def test_direct_fixing_rule_only_calls_after_negative_pre_move(self):
        d = datetime(2026, 1, 5).date()
        fix = local_time(d, 14, 15, BERLIN)
        start = local_time(d, 7, 0, BERLIN)
        minutes = int((fix-start).total_seconds()//60)
        by_ts = {}
        bars = []
        for i in range(minutes + 60):
            ts = start + timedelta(minutes=i)
            px = 1.12 - i * 0.000001 if i < minutes else 1.12 - minutes*0.000001 + (i-minutes)*0.00001
            b = Bar(ts, px, px, px, px)
            by_ts[ts] = b
            bars.append(b)
        result = fixing_events(bars, by_ts)
        info = result["FXFIX-ECB-PREFIX-USD-REV-CALL"]
        self.assertEqual(info["raw_signal_events"], 1)
        self.assertEqual(info["events"][0]["side"], "CALL")


if __name__ == "__main__":
    unittest.main()
