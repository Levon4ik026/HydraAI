import unittest
from datetime import datetime, timedelta, timezone

from research.intratrade_path_audit import build_events, paired_day_bootstrap


def row(ts, signal=0, adx=20, o=1.1000, h=1.1005, l=1.0995, c=1.1001, seg=0):
    return {
        "bar": type("Bar", (), {
            "timestamp": ts, "open": o, "high": h, "low": l, "close": c
        })(),
        "signal": signal, "adx": adx, "segment_id": seg,
    }


class IntratradePathAuditTests(unittest.TestCase):
    def test_builds_five_horizons_from_next_open(self):
        t = datetime(2026, 10, 1, tzinfo=timezone.utc)
        rows = [
            row(t, signal=1),
            row(t + timedelta(minutes=5), o=1.1000, h=1.1010, l=1.0998, c=1.1005),
            row(t + timedelta(minutes=10), o=1.1005, h=1.1015, l=1.1000, c=1.1010),
            row(t + timedelta(minutes=15), o=1.1010, h=1.1015, l=1.1005, c=1.1008),
            row(t + timedelta(minutes=20), o=1.1008, h=1.1012, l=1.1002, c=1.1009),
            row(t + timedelta(minutes=25), o=1.1009, h=1.1014, l=1.1007, c=1.1012),
        ]
        events = build_events(rows)
        self.assertEqual([x["h"] for x in events], [1, 2, 3, 4, 5])
        self.assertEqual(events[0]["outcome"], "WIN")
        self.assertGreaterEqual(events[4]["mfe_pips"], events[0]["mfe_pips"])
        self.assertGreaterEqual(events[4]["mae_pips"], events[0]["mae_pips"])

    def test_does_not_cross_segment_gap(self):
        t = datetime(2026, 10, 1, tzinfo=timezone.utc)
        rows = [
            row(t, signal=-1),
            row(t + timedelta(minutes=5), seg=0),
            row(t + timedelta(minutes=10), seg=1),
            row(t + timedelta(minutes=15), seg=1),
        ]
        events = build_events(rows)
        self.assertEqual([x["h"] for x in events], [1])

    def test_paired_bootstrap_is_reproducible(self):
        t = datetime(2026, 10, 1, tzinfo=timezone.utc)
        rows = [row(t, signal=1)]
        for i in range(1, 7):
            rows.append(row(t + timedelta(minutes=5*i), o=1.1, h=1.101, l=1.099, c=1.1001))
        events = build_events(rows)
        a = paired_day_bootstrap(events, reps=1000, seed=42)
        b = paired_day_bootstrap(events, reps=1000, seed=42)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
