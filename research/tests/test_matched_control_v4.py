import unittest
from datetime import datetime, timedelta, timezone

from research.matched_control_block_bootstrap_v4 import match_controls, time_overlaps_any


class MatchedControlV4Tests(unittest.TestCase):
    def row(self, when, segment, index, outcome="W"):
        return {"time": when, "period": "TRAIN", "segment": segment,
                "index": index, "outcome": outcome}

    def test_same_date_neighbor_is_rejected_for_nearest_other_date(self):
        event_time = datetime(2025, 1, 6, 10, 30, tzinfo=timezone.utc)
        event = self.row(event_time, 1, 100, "L")
        same_date_neighbor = self.row(event_time + timedelta(minutes=5), 2, 101, "W")
        previous_week = self.row(event_time - timedelta(days=7), 3, 100, "W")
        pairs = match_controls({"expiry_bars": 1, "nonoverlap": True},
                               [event], [same_date_neighbor, previous_week])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1]["segment"], 3)
        self.assertNotEqual(pairs[0][0]["time"].date(), pairs[0][1]["time"].date())

    def test_one_control_per_calendar_date_and_hour(self):
        base = datetime(2025, 1, 20, 10, 0, tzinfo=timezone.utc)
        events = [
            self.row(base, 1, 100, "L"),
            self.row(base + timedelta(minutes=30), 1, 106, "L"),
        ]
        controls = [
            self.row(base - timedelta(days=7), 2, 100, "W"),
            self.row(base - timedelta(days=7) + timedelta(minutes=30), 2, 106, "W"),
            self.row(base + timedelta(days=7), 3, 100, "W"),
            self.row(base + timedelta(days=7) + timedelta(minutes=30), 3, 106, "W"),
        ]
        pairs = match_controls({"expiry_bars": 1, "nonoverlap": True}, events, controls)
        self.assertEqual(len(pairs), 2)
        dates = [control["time"].date() for _, control in pairs]
        self.assertEqual(len(set(dates)), 2)

    def test_cross_segment_matching_is_preserved(self):
        event_time = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        event = self.row(event_time, 1, 100, "L")
        control = self.row(event_time - timedelta(days=7), 2, 100, "W")
        pairs = match_controls({"expiry_bars": 12, "nonoverlap": True},
                               [event], [control])
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1]["segment"], 2)

    def test_no_pair_when_only_same_date_controls_exist(self):
        event_time = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        event = self.row(event_time, 1, 100, "L")
        same_date = self.row(event_time + timedelta(minutes=5), 2, 101, "W")
        pairs = match_controls({"expiry_bars": 1, "nonoverlap": True},
                               [event], [same_date])
        self.assertEqual(pairs, [])

    def test_selected_control_windows_are_globally_nonoverlapping(self):
        t1 = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        t2 = t1 + timedelta(days=7)
        events = [self.row(t1, 1, 10, "L"), self.row(t2, 1, 30, "L")]
        controls = [
            self.row(t1 - timedelta(days=7), 2, 10, "W"),
            self.row(t1 - timedelta(days=7) + timedelta(minutes=30), 3, 10, "W"),
        ]
        pairs = match_controls({"expiry_bars": 12, "nonoverlap": True}, events, controls)
        self.assertLessEqual(len(pairs), 1)

    def test_half_open_interval_boundary_does_not_overlap(self):
        duration = timedelta(minutes=60)
        start = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)
        self.assertFalse(time_overlaps_any(start + duration, [start], duration))
        self.assertTrue(time_overlaps_any(start + duration - timedelta(seconds=1), [start], duration))


if __name__ == "__main__":
    unittest.main()
