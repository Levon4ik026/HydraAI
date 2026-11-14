import csv
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import three_candidate_forward_validation as forward


UTC = timezone.utc


class ForwardDataTests(unittest.TestCase):
    def write_source(self, path, rows):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("timestamp", "open", "high", "low", "close"))
            writer.writerows(rows)

    def test_warmup_and_forward_are_split_and_duplicates_are_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.csv"
            self.write_source(path, [
                ("2026-11-01T23:59:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-09T23:59:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-10T00:00:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-10T00:00:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-10T00:01:00Z", 1.1, 1.0, 1.2, 1.1),
            ])
            warmup, fresh, stats = forward.load_split_bars(
                path, date(2026, 11, 2), date(2026, 11, 10), date(2026, 11, 10)
            )
            self.assertEqual(len(warmup), 1)
            self.assertEqual(len(fresh), 1)
            self.assertEqual(stats["invalid_rows"], 1)
            self.assertEqual(stats["duplicate_timestamp_rows"], 1)
            self.assertEqual(stats["out_of_range_rows"], 1)
            self.assertEqual(fresh[0].timestamp, datetime(2026, 11, 10, tzinfo=UTC))

    def test_conflicting_duplicate_timestamp_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.csv"
            self.write_source(path, [
                ("2026-11-09T23:59:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-10T00:00:00Z", 1.1, 1.2, 1.0, 1.1),
                ("2026-11-10T00:00:00Z", 1.1, 1.2, 1.0, 1.1001),
            ])
            with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
                forward.load_split_bars(
                    path, date(2026, 11, 2), date(2026, 11, 10), date(2026, 11, 10)
                )

    def test_missing_forward_data_is_not_backfilled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.csv"
            self.write_source(path, [
                ("2026-11-09T23:59:00Z", 1.1, 1.2, 1.0, 1.1),
            ])
            with self.assertRaisesRegex(ValueError, "No new M1 observations"):
                forward.load_split_bars(
                    path, date(2026, 11, 2), date(2026, 11, 10), date(2026, 11, 10)
                )

    def test_m5_builder_splits_at_missing_bucket(self):
        bars = []
        start = datetime(2026, 11, 10, tzinfo=UTC)
        for offset in list(range(5)) + list(range(10, 15)):
            stamp = start + timedelta(minutes=offset)
            bars.append(forward.Bar(stamp, 1.1, 1.101, 1.099, 1.1005))
        segments = forward.make_m5(bars)
        self.assertEqual(len(segments), 2)
        self.assertEqual([len(segment) for segment in segments], [1, 1])


class FrozenDefinitionTests(unittest.TestCase):
    def valid_config(self):
        rows = []
        for candidate_id, values in forward.FROZEN.items():
            event_type, side, expiry, nonoverlap, min_index, tail_guard, level = values
            row = {
                "id": candidate_id,
                "event_type": event_type,
                "side": side,
                "expiry_bars": expiry,
                "nonoverlap": nonoverlap,
                "min_signal_index": min_index,
                "tail_guard": tail_guard,
                "split_settlement": "bar_close",
            }
            if level is not None:
                row["background_requires_level"] = level
            rows.append(row)
        return {"dataset": {"snapshot_id": "frozen-baseline"}, "candidates": rows}

    def test_exact_three_frozen_definitions_are_required(self):
        config = self.valid_config()
        forward.validate_candidate_config(config)
        config["candidates"][0]["expiry_bars"] = 2
        with self.assertRaisesRegex(ValueError, "Frozen definition drift"):
            forward.validate_candidate_config(config)


class MetricsTests(unittest.TestCase):
    def test_payout_drawdown_streak_and_coverage_metrics(self):
        start = datetime(2026, 11, 10, 12, tzinfo=UTC)
        trades = [
            {"outcome": "L", "entry_time": start, "signal_time": start - timedelta(minutes=5)},
            {"outcome": "L", "entry_time": start + timedelta(minutes=5), "signal_time": start},
            {"outcome": "W", "entry_time": start + timedelta(days=1), "signal_time": start + timedelta(days=1) - timedelta(minutes=5)},
            {"outcome": "D", "entry_time": start + timedelta(days=1, minutes=5), "signal_time": start + timedelta(days=1)},
        ]
        metrics = forward.summarize_metrics(
            trades, {date(2026, 11, 10), date(2026, 11, 11)}
        )
        self.assertEqual((metrics["w"], metrics["l"], metrics["d"]), (1, 2, 1))
        self.assertAlmostEqual(metrics["wr_pct"], 100.0 / 3.0, places=3)
        self.assertAlmostEqual(metrics["wilson_95_pct"][0], 6.15, places=2)
        self.assertAlmostEqual(metrics["wilson_95_pct"][1], 79.23, places=2)
        self.assertAlmostEqual(metrics["wins_all_pct"], 25.0, places=4)
        self.assertAlmostEqual(metrics["net_92_units"], -1.08, places=8)
        self.assertAlmostEqual(metrics["roi_92_pct"], -27.0, places=4)
        self.assertAlmostEqual(metrics["profit_factor_92"], 0.46, places=8)
        self.assertAlmostEqual(metrics["max_drawdown_92_units"], 2.0, places=8)
        self.assertEqual(metrics["longest_losing_streak"], 2)
        self.assertEqual(metrics["active_days"], 2)
        self.assertEqual(metrics["observed_forward_days"], 2)
        self.assertAlmostEqual(metrics["payout_sensitivity"]["0.50"], -1.5, places=8)
        self.assertEqual(metrics["sample_status"], "DESCRIPTIVE_ONLY_INSUFFICIENT_N")
        self.assertEqual(metrics["weekly_stability"][0]["n"], 4)

    def test_empty_metrics_have_no_undefined_ratios(self):
        metrics = forward.summarize_metrics([], set())
        self.assertIsNone(metrics["wr_pct"])
        self.assertIsNone(metrics["wilson_95_pct"])
        self.assertIsNone(metrics["wins_all_pct"])
        self.assertIsNone(metrics["roi_92_pct"])
        self.assertIsNone(metrics["profit_factor_92"])


class ForwardBoundaryTests(unittest.TestCase):
    def test_pre_start_trade_crossing_boundary_is_purged(self):
        start = datetime(2026, 11, 9, tzinfo=UTC)
        bars = []
        for index in range(330):
            stamp = start + timedelta(minutes=5 * index)
            bars.append({
                "bar_index": index,
                "timestamp": stamp,
                "open": 1.1000,
                "high": 1.1010,
                "low": 1.0990,
                "close": 1.1005,
                "rsi14": 50.0,
            })
        for index in (287, 288):
            bars[index]["rsi14"] = 75.0
            bars[index]["close"] = 1.0990
        bars[289]["close"] = 1.1010

        candidate = {
            "id": "HYD-CAND-001",
            "event_type": "rsi_bearish_level",
            "side": "PUT",
            "expiry_bars": 1,
            "nonoverlap": False,
            "min_signal_index": 60,
            "tail_guard": 13,
            "split_settlement": "bar_close",
        }
        forward_start = datetime(2026, 11, 10, tzinfo=UTC)
        result = forward.evaluate_candidate(
            candidate,
            {0: bars},
            forward_start,
            datetime(2026, 11, 11, tzinfo=UTC),
            {date(2026, 11, 10)},
        )
        self.assertEqual(result["metrics"]["n"], 1)
        self.assertEqual(result["metrics"]["sample_status"], "DESCRIPTIVE_ONLY_INSUFFICIENT_N")
        self.assertEqual(result["raw_forward_events"], 1)
        self.assertGreater(result["boundary_purged_m5_windows"], 0)


if __name__ == "__main__":
    unittest.main()
