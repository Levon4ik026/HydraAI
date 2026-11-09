import csv
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mean_reversion_frozen_holdout import (
    HOLDOUT_START, Bar, prior_close_zscore, event_stream, outcome,
    nonoverlap, classify_period, random_direction_baseline,
    load_dukascope_m1,
)


class FrozenMeanReversionTests(unittest.TestCase):
    def make_bars(self, closes, current_open, current_close, entry_open, entry_close):
        start = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)
        bars = []
        for i, close in enumerate(closes):
            bars.append(Bar(start + timedelta(minutes=5 * i), close, close, close, close))
        idx = len(closes)
        bars.append(Bar(start + timedelta(minutes=5 * idx),
                        current_open, max(current_open, current_close),
                        min(current_open, current_close), current_close))
        bars.append(Bar(start + timedelta(minutes=5 * (idx + 1)),
                        entry_open, max(entry_open, entry_close),
                        min(entry_open, entry_close), entry_close))
        return bars

    def test_prior_zscore_uses_exact_previous_20_closes_and_population_std(self):
        closes = [100.0] * 19 + [99.0]
        bars = [Bar(datetime(2026, 11, 9, tzinfo=timezone.utc) + timedelta(minutes=5*i),
                    x, x, x, x) for i, x in enumerate(closes)]
        z = prior_close_zscore(bars, 20)
        self.assertIsNotNone(z)
        self.assertLess(z, -1.5)

    def test_frozen_call_requires_bullish_close_above_previous(self):
        closes = [100.0] * 19 + [99.0]
        bars = self.make_bars(closes, 99.02, 99.10, 99.08, 99.14)
        segments = [bars]
        events = event_stream(segments, "CALL")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["index"], 20)
        self.assertEqual(outcome(events[0]["delta"], "CALL"), "W")
        self.assertEqual(outcome(events[0]["delta"], "PUT"), "L")

    def test_mirror_put_is_separate_and_directional(self):
        closes = [100.0] * 19 + [101.0]
        bars = self.make_bars(closes, 100.98, 100.90, 100.92, 100.84)
        events = event_stream([bars], "PUT")
        self.assertEqual(len(events), 1)
        self.assertEqual(outcome(events[0]["delta"], "PUT"), "W")
        self.assertEqual(outcome(events[0]["delta"], "CALL"), "L")

    def test_nonoverlap_allows_next_signal_after_prior_entry_candle_closes(self):
        base = datetime(2026, 11, 9, tzinfo=timezone.utc)
        events = [
            {"segment": 0, "index": 10, "signal_time": base, "delta": 0.1},
            {"segment": 0, "index": 11, "signal_time": base + timedelta(minutes=5), "delta": -0.1},
            {"segment": 0, "index": 11, "signal_time": base + timedelta(minutes=5), "delta": 0.2},
        ]
        accepted = nonoverlap(events)
        self.assertEqual(len(accepted), 2)
        self.assertEqual([x["index"] for x in accepted], [10, 11])

    def test_split_boundary_crossing_is_purged(self):
        d1 = datetime(2026, 11, 10).date()
        d2 = datetime(2026, 11, 11).date()
        signal = datetime(2026, 11, 9, 23, 55, tzinfo=timezone.utc)
        settle = datetime(2026, 11, 10, 0, 5, tzinfo=timezone.utc)
        self.assertIsNone(classify_period(signal, settle, d1, d2,
                                          datetime(2026, 11, 12, tzinfo=timezone.utc)))
        fresh_signal = HOLDOUT_START
        fresh_settle = HOLDOUT_START + timedelta(minutes=10)
        self.assertEqual(classify_period(fresh_signal, fresh_settle, d1, d2,
                                         HOLDOUT_START + timedelta(days=1)), "FRESH HOLDOUT")

    def test_random_baseline_is_reproducible_on_fixed_events(self):
        events = [{"delta": 0.01}, {"delta": -0.01}, {"delta": 0.0}]
        a = random_direction_baseline(events, 0.92, 1234)
        b = random_direction_baseline(events, 0.92, 1234)
        self.assertEqual(a, b)
        self.assertEqual(a["n"], 3)
        self.assertEqual(a["draws"], 1)

    def test_source_audit_hash_and_complete_m5_bars(self):
        start = HOLDOUT_START
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "duka.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
                for i in range(10):
                    ts = start + timedelta(minutes=i)
                    ms = int(ts.timestamp() * 1000)
                    price = 1.1 + i * 0.00001
                    writer.writerow([ms, price, price + 0.00002, price - 0.00002, price + 0.00001, 1])
            snapshot = start + timedelta(minutes=10)
            m1, segments, meta = load_dukascope_m1(path, snapshot)
            self.assertEqual(len(m1), 10)
            self.assertEqual(meta["raw_rows"], 10)
            self.assertEqual(meta["complete_m5_bars"], 2)
            self.assertEqual(meta["m5_segments"], 1)
            self.assertEqual(meta["holdout_m5_bars"], 2)
            self.assertEqual(len(meta["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
