from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from research.watch_frozen_put_candidate import (
    load_m1, load_or_create_state, next_m5_boundary,
)


class PutForwardMonitorTests(unittest.TestCase):
    def test_next_m5_boundary_rounds_forward(self):
        now = datetime(2026, 11, 7, 13, 2, 44, tzinfo=timezone.utc)
        self.assertEqual(
            next_m5_boundary(now),
            datetime(2026, 11, 7, 13, 5, tzinfo=timezone.utc),
        )

    def test_next_m5_boundary_at_boundary_advances_one_bucket(self):
        now = datetime(2026, 11, 7, 13, 5, 0, tzinfo=timezone.utc)
        self.assertEqual(
            next_m5_boundary(now),
            datetime(2026, 11, 7, 13, 10, tzinfo=timezone.utc),
        )

    def test_forward_start_is_persisted_and_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            start = "2026-11-07T13:10:00Z"
            state = load_or_create_state(state_path, start)
            self.assertEqual(state["forward_start"], "2026-11-07T13:10:00+00:00")
            self.assertTrue(state_path.exists())
            with self.assertRaises(SystemExit):
                load_or_create_state(state_path, "2026-11-07T13:15:00Z")
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["forward_start"], state["forward_start"])

    def test_default_forward_start_is_frozen_at_first_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            fixed_now = datetime(2026, 11, 7, 13, 2, 44, tzinfo=timezone.utc)
            with patch("research.watch_frozen_put_candidate.utc_now", return_value=fixed_now):
                state = load_or_create_state(state_path, None)
            self.assertEqual(state["forward_start"], "2026-11-07T13:05:00+00:00")
            with patch("research.watch_frozen_put_candidate.utc_now",
                       return_value=datetime(2026, 11, 7, 15, 0, tzinfo=timezone.utc)):
                restarted = load_or_create_state(state_path, None)
            self.assertEqual(restarted["forward_start"], state["forward_start"])

    def test_csv_loader_sorts_and_rejects_conflicting_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candles.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["datetime_utc", "open", "high", "low", "close"]
                )
                writer.writeheader()
                writer.writerow({
                    "datetime_utc": "2026-11-07T13:01:00Z",
                    "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.15,
                })
                writer.writerow({
                    "datetime_utc": "2026-11-07T13:00:00Z",
                    "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.12,
                })
            rows = load_m1(path)
            self.assertEqual(len(rows), 2)
            self.assertLess(rows[0].timestamp, rows[1].timestamp)

            with path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["datetime_utc", "open", "high", "low", "close"]
                )
                writer.writerow({
                    "datetime_utc": "2026-11-07T13:01:00Z",
                    "open": 1.1, "high": 1.2, "low": 1.0, "close": 1.16,
                })
            with self.assertRaises(ValueError):
                load_m1(path)


if __name__ == "__main__":
    unittest.main()
