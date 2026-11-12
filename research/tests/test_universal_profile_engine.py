import unittest
from datetime import datetime, timedelta, timezone

from research.universal_profile_engine import build_candidate_events, win_loss


class UniversalProfileEngineTests(unittest.TestCase):
    def make_segment(self, n=110, start=None):
        start = start or datetime(2025, 1, 6, tzinfo=timezone.utc)
        rows = []
        for i in range(n):
            o = 1.1000
            rows.append({
                "bar_index": i, "timestamp": start + timedelta(minutes=5*i),
                "open": o, "high": 1.1010, "low": 1.0990, "close": 1.1005,
                "rsi14": 50.0, "previous_observed_utc_week_low": 1.0950,
                "ema20_50_bias": "UP", "adx_band": "MID_20_30",
                "atr_vol_band": "HIGH_GT67", "momentum6_band": "UP_GT1",
            })
        return rows

    def test_binary_outcome_mapping_and_draw(self):
        self.assertEqual(win_loss(-0.001, "PUT"), "W")
        self.assertEqual(win_loss(0.001, "PUT"), "L")
        self.assertEqual(win_loss(0.001, "CALL"), "W")
        self.assertEqual(win_loss(0.0, "CALL"), "D")

    def test_rsi_events_preserve_adjacent_nonoverlapping_expiry_schedule(self):
        bars = self.make_segment()
        for i in (65, 66):
            bars[i]["rsi14"] = 75.0
            bars[i]["close"] = 1.0995
            bars[i]["open"] = 1.1000
        bars[66]["close"] = 1.0990
        bars[67]["close"] = 1.0990
        candidate = {
            "event_type": "rsi_bearish_level", "side": "PUT",
            "expiry_bars": 1, "nonoverlap": False,
        }
        d1 = datetime(2025, 9, 17, tzinfo=timezone.utc)
        d2 = datetime(2026, 4, 14, tzinfo=timezone.utc)
        accepted, background, purged = build_candidate_events(candidate, {0: bars}, d1, d2)
        self.assertEqual(len(accepted), 2)
        self.assertEqual([x["outcome"] for x in accepted], ["W", "W"])
        self.assertEqual(purged, 0)
        self.assertFalse(any(x["index"] in (65, 66) for x in background))

    def test_sweep_reclaim_nonoverlap_blocks_overlapping_events(self):
        bars = self.make_segment()
        for i in (65, 66):
            bars[i]["low"] = 1.0940
            bars[i]["open"] = 1.1000
            bars[i]["close"] = 1.1005
        for i in (71, 72):
            bars[i]["close"] = 1.0990
        candidate = {
            "event_type": "previous_week_low_sweep_reclaim_bullish",
            "side": "PUT", "expiry_bars": 6, "nonoverlap": True,
        }
        d1 = datetime(2025, 9, 17, tzinfo=timezone.utc)
        d2 = datetime(2026, 4, 14, tzinfo=timezone.utc)
        accepted, _, purged = build_candidate_events(candidate, {0: bars}, d1, d2)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["index"], 65)
        self.assertEqual(purged, 0)


if __name__ == "__main__":
    unittest.main()
