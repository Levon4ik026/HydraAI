import random
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RESEARCH_DIR))

from cand013_dependence_audit import (  # noqa: E402
    bootstrap,
    calendar_days,
    day_block_sample,
    paired_difference_bootstrap,
)


class Cand013CalendarBlockTests(unittest.TestCase):
    def test_calendar_grid_contains_zero_trade_dates(self):
        days = calendar_days(date(2026, 11, 1), date(2026, 11, 10))
        self.assertEqual(len(days), 10)
        self.assertEqual(days[0], date(2026, 11, 1))
        self.assertEqual(days[-1], date(2026, 11, 10))
        self.assertTrue(all((b - a).days == 1 for a, b in zip(days, days[1:])))

    def test_sampled_blocks_are_contiguous_and_do_not_wrap(self):
        days = calendar_days(date(2026, 1, 1), date(2026, 1, 20))
        sampled = day_block_sample(days, block=4, rng=random.Random(17))
        self.assertEqual(len(sampled), len(days))
        for offset in range(0, len(sampled), 4):
            block = sampled[offset:offset + 4]
            self.assertTrue(all((b - a).days == 1 for a, b in zip(block, block[1:])))

    def test_bootstrap_is_reproducible_with_zero_event_days_and_split_strata(self):
        train_start = date(2026, 1, 1)
        val_start = date(2026, 2, 1)
        ranges = {
            "TRAIN": (train_start, train_start + timedelta(days=29)),
            "VALIDATION": (val_start, val_start + timedelta(days=29)),
        }
        rows = []
        for split, start in (("TRAIN", train_start), ("VALIDATION", val_start)):
            for offset, outcome in ((0, "W"), (5, "L"), (12, "W"), (21, "L"), (28, "W")):
                rows.append({
                    "split": split,
                    "day": start + timedelta(days=offset),
                    "result": outcome,
                })
        first = bootstrap(rows, block=3, reps=300, seed=20261111, split_ranges=ranges)
        second = bootstrap(rows, block=3, reps=300, seed=20261111, split_ranges=ranges)
        self.assertIsNotNone(first)
        self.assertEqual(first, second)

    def test_paired_bootstrap_keeps_analog_and_control_on_same_days(self):
        start = date(2026, 3, 1)
        ranges = {"TRAIN": (start, start + timedelta(days=29))}
        rows = []
        for offset in (0, 4, 8, 12, 16, 20, 24, 28):
            day = start + timedelta(days=offset)
            rows.append({"split": "TRAIN", "day": day, "result": "W", "analog": True})
            rows.append({"split": "TRAIN", "day": day, "result": "L", "analog": False})
        result = paired_difference_bootstrap(
            rows, block=3, reps=300, seed=23, split_ranges=ranges
        )
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0], 100.0)
        self.assertAlmostEqual(result[1], 100.0)
        self.assertAlmostEqual(result[2], 100.0)


if __name__ == "__main__":
    unittest.main()
