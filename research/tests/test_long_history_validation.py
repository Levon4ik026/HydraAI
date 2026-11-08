import unittest
from datetime import date, datetime, timezone

from research.long_history_validation import m5_close_time, split_records


def row(signal_day, settle_day, direction="CALL"):
    return {
        "signal_time": datetime.fromisoformat(signal_day + "T23:58:00+00:00"),
        "settle_time": datetime.fromisoformat(settle_day + "T00:02:00+00:00"),
        "direction": direction,
        "outcome": "WIN",
    }


class LongHistorySplitTests(unittest.TestCase):
    def test_purges_trades_that_settle_across_split_boundaries(self):
        records = [
            row("2026-09-16", "2026-09-16"),
            row("2026-09-16", "2026-09-17"),
            row("2026-09-17", "2026-09-18"),
            row("2026-09-18", "2026-09-19"),
            row("2026-09-19", "2026-09-20"),
        ]
        splits, purged = split_records(records, date(2026, 9, 17), date(2026, 9, 19))
        self.assertEqual(len(splits["TRAIN"]), 1)
        self.assertEqual(len(splits["VALIDATION"]), 1)
        self.assertEqual(len(splits["TEST"]), 1)
        self.assertEqual(purged, {"TRAIN": 1, "VALIDATION": 1})
        self.assertEqual(len(splits["ALL"]), 5)


    def test_m5_bar_settling_exactly_at_midnight_is_purged(self):
        bar_open = datetime(2026, 9, 16, 23, 55, tzinfo=timezone.utc)
        settlement = m5_close_time(bar_open)
        self.assertEqual(settlement, datetime(2026, 9, 17, 0, 0, tzinfo=timezone.utc))
        records = [{
            "signal_time": bar_open,
            "settle_time": settlement,
            "direction": "CALL",
            "outcome": "WIN",
        }]
        splits, purged = split_records(records, date(2026, 9, 17), date(2026, 9, 19))
        self.assertEqual(splits["TRAIN"], [])
        self.assertEqual(purged["TRAIN"], 1)

    def test_trade_settling_on_boundary_is_purged(self):
        records = [row("2026-09-18", "2026-09-19")]
        splits, purged = split_records(records, date(2026, 9, 17), date(2026, 9, 19))
        self.assertEqual(splits["VALIDATION"], [])
        self.assertEqual(purged["VALIDATION"], 1)


if __name__ == "__main__":
    unittest.main()
