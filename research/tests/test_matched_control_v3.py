import unittest
from datetime import datetime, timedelta, timezone

from research.matched_control_block_bootstrap_v3 import match_controls, time_overlaps_any


class MatchedControlV3Tests(unittest.TestCase):
    def row(self, when, segment, index, outcome="W"):
        return {"time": when, "period": "TRAIN", "segment": segment,
                "index": index, "outcome": outcome}

    def test_cross_segment_control_can_match_same_weekday_hour(self):
        event_time = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        control_time = event_time - timedelta(days=7)
        event = self.row(event_time, 1, 100, "L")
        control = self.row(control_time, 2, 100, "W")
        pairs = match_controls({"expiry_bars": 12, "nonoverlap": True},
                               [event], [control])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1]["segment"], 2)

    def test_control_inside_candidate_window_is_rejected(self):
        event_time = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        event = self.row(event_time, 1, 100, "L")
        overlapping = self.row(event_time + timedelta(minutes=30), 2, 20, "W")
        safe = self.row(event_time - timedelta(days=7), 3, 20, "W")
        pairs = match_controls({"expiry_bars": 12, "nonoverlap": True},
                               [event], [overlapping, safe])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1]["segment"], 3)

    def test_selected_control_windows_are_globally_nonoverlapping(self):
        t1 = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(days=7)
        e1 = self.row(t1, 1, 10, "L")
        e2 = self.row(t2, 1, 30, "L")
        c1 = self.row(t1 - timedelta(days=7), 2, 10, "W")
        c2 = self.row(t1 - timedelta(days=7) + timedelta(minutes=30), 3, 10, "W")
        pairs = match_controls({"expiry_bars": 12, "nonoverlap": True},
                               [e1, e2], [c1, c2])
        self.assertLessEqual(len(pairs), 1)

    def test_half_open_interval_boundary_does_not_overlap(self):
        duration = timedelta(minutes=60)
        starts = [datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)]
        self.assertFalse(time_overlaps_any(starts[0] + duration, starts, duration))
        self.assertTrue(time_overlaps_any(starts[0] + duration - timedelta(seconds=1), starts, duration))


if __name__ == "__main__":
    unittest.main()
