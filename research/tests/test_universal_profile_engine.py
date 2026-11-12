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

    def test_additional_frozen_event_families(self):
        d1 = datetime(2025, 9, 17, tzinfo=timezone.utc)
        d2 = datetime(2026, 4, 14, tzinfo=timezone.utc)
        cases = [
            ("previous_day_high_sweep_reclaim_bearish", "CALL"),
            ("previous_day_low_close_breakout", "CALL"),
            ("ema20_bearish_cross", "CALL"),
            ("donchian50_bullish_breakout", "PUT"),
            ("bullish_abnormal_impulse", "PUT"),
            ("up_shock_second_bar_reversal", "PUT"),
        ]
        for event_type, side in cases:
            bars = self.make_segment()
            i = 65
            if event_type == "previous_day_high_sweep_reclaim_bearish":
                bars[i].update(previous_observed_utc_day_high="1.1050",
                               open=1.1050, high=1.1060, low=1.1030, close=1.1040)
            elif event_type == "previous_day_low_close_breakout":
                bars[i-1]["close"] = 1.0960
                bars[i].update(previous_observed_utc_day_low="1.0950",
                               open=1.0960, high=1.0970, low=1.0930, close=1.0940)
            elif event_type == "ema20_bearish_cross":
                bars[i-1].update(ema20=1.1010, ema50=1.1000)
                bars[i].update(ema20=1.0990, ema50=1.1000, close=1.0980)
            elif event_type == "donchian50_bullish_breakout":
                bars[i].update(open=1.1000, high=1.1030, low=1.0990, close=1.1020)
            elif event_type == "bullish_abnormal_impulse":
                bars[i].update(open=1.1000, high=1.1040, low=1.0990, close=1.1030)
            elif event_type == "up_shock_second_bar_reversal":
                bars[i-1].update(open=1.1000, high=1.1050, low=1.1000, close=1.1040)
                bars[i].update(open=1.1030, high=1.1035, low=1.1015, close=1.1020)
            candidate = {"event_type": event_type, "side": side,
                         "expiry_bars": 1, "nonoverlap": False}
            accepted, _, purged = build_candidate_events(candidate, {0: bars}, d1, d2)
            self.assertEqual([x["index"] for x in accepted], [i], event_type)
            self.assertEqual(purged, 0, event_type)

    def test_candidate_specific_split_settlement_open_vs_close(self):
        start = datetime(2025, 9, 16, 18, 25, tzinfo=timezone.utc)
        bars = self.make_segment(start=start)
        i = 65  # signal candle opens 23:50 UTC; H=1 settlement candle opens 23:55.
        bars[i]["rsi14"] = 75.0
        bars[i]["open"] = 1.1000
        bars[i]["close"] = 1.0990
        d1 = datetime(2025, 9, 17, tzinfo=timezone.utc)
        d2 = datetime(2026, 4, 14, tzinfo=timezone.utc)
        base = {"event_type": "rsi_bearish_level", "side": "PUT",
                "expiry_bars": 1, "nonoverlap": False}
        open_mode, _, purged_open = build_candidate_events(
            {**base, "split_settlement": "bar_open"}, {0: bars}, d1, d2)
        close_mode, _, purged_close = build_candidate_events(
            {**base, "split_settlement": "bar_close"}, {0: bars}, d1, d2)
        self.assertTrue(any(x["index"] == i for x in open_mode))
        self.assertFalse(any(x["index"] == i for x in close_mode))
        self.assertEqual(purged_open, 0)
        self.assertEqual(purged_close, 1)


if __name__ == "__main__":
    unittest.main()
