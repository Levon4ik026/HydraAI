import csv
import tempfile
import unittest
from pathlib import Path

from research.data_audit import audit_csv


class DataAuditTests(unittest.TestCase):
    def make_csv(self, rows):
        temp = tempfile.TemporaryDirectory()
        path = Path(temp.name) / "candles.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["timestamp", "open", "high", "low", "close"])
            writer.writerows(rows)
        self.addCleanup(temp.cleanup)
        return path

    def test_clean_minute_series(self):
        path = self.make_csv([
            ["2026-01-05T10:00:00Z", 1.1, 1.2, 1.0, 1.15],
            ["2026-01-05T10:01:00Z", 1.15, 1.2, 1.1, 1.18],
            ["2026-01-05T10:02:00Z", 1.18, 1.2, 1.17, 1.19],
        ])
        result = audit_csv(path)
        self.assertEqual(result["summary"]["parsed_rows"], 3)
        self.assertEqual(result["summary"]["gap_count"], 0)
        self.assertEqual(result["summary"]["invalid_ohlc_rows"], 0)

    def test_gap_and_duplicate_are_reported(self):
        path = self.make_csv([
            ["2026-01-05T10:00:00Z", 1.1, 1.2, 1.0, 1.15],
            ["2026-01-05T10:01:00Z", 1.15, 1.2, 1.1, 1.18],
            ["2026-01-05T10:01:00Z", 1.15, 1.2, 1.1, 1.18],
            ["2026-01-05T10:04:00Z", 1.18, 1.2, 1.17, 1.19],
        ])
        result = audit_csv(path)
        self.assertEqual(result["summary"]["duplicate_timestamp_groups"], 1)
        self.assertEqual(result["summary"]["gap_count"], 1)
        self.assertEqual(result["gaps"][0]["missing_expected_bars"], 2)

    def test_invalid_ohlc_is_not_silently_dropped(self):
        path = self.make_csv([
            ["2026-01-05T10:00:00Z", 1.1, 1.0, 1.05, 1.15],
        ])
        result = audit_csv(path)
        self.assertEqual(result["summary"]["parsed_rows"], 1)
        self.assertEqual(result["summary"]["invalid_ohlc_rows"], 1)
        self.assertEqual(result["issues"][0]["type"], "invalid_ohlc")

    def test_epoch_milliseconds_and_header_aliases(self):
        path = self.make_csv([
            [1767607200000, 1.1, 1.2, 1.0, 1.15],
            [1767607260000, 1.15, 1.2, 1.1, 1.18],
        ])
        # Rewrite headers to common one-letter OHLC aliases.
        content = path.read_text(encoding="utf-8")
        path.write_text(content.replace("timestamp,open,high,low,close", "time,o,h,l,c"), encoding="utf-8")
        result = audit_csv(path)
        self.assertEqual(result["summary"]["parsed_rows"], 2)
        self.assertEqual(result["summary"]["gap_count"], 0)


if __name__ == "__main__":
    unittest.main()
