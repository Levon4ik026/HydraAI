import unittest
from datetime import datetime, timedelta, timezone

from reproduce_m5_bb_williams_adx import Bar
from research.nonoverlap_baseline_audit import (
    make_momentum_events, metrics, schedule_non_overlapping, score_events,
)


def bars(closes):
    start = datetime(2026, 1, 5, 10, 0, tzinfo=timezone.utc)
    out = []
    previous = closes[0]
    for i, close in enumerate(closes):
        stamp = start + timedelta(minutes=5 * i)
        o = previous
        out.append(Bar(stamp, o, max(o, close) + 0.001, min(o, close) - 0.001, close))
        previous = close
    return out


class NonOverlapBaselineAuditTests(unittest.TestCase):
    def event(self, index, segment=0, direction="CALL"):
        return {
            "signal_time": datetime(2026, 1, 5, 10, tzinfo=timezone.utc) + timedelta(minutes=5 * index),
            "segment": segment,
            "bar_index": index,
            "direction": direction,
        }

    def test_suppresses_active_signals_but_allows_expiry_close_signal(self):
        events = [self.event(i) for i in (1, 2, 3, 4, 5)]
        accepted = schedule_non_overlapping(events, horizon_bars=2)
        self.assertEqual([x["bar_index"] for x in accepted], [1, 3, 5])

    def test_scheduler_resets_for_each_continuous_segment(self):
        events = [self.event(4, segment=0), self.event(0, segment=1)]
        accepted = schedule_non_overlapping(events, horizon_bars=3)
        self.assertEqual([(x["segment"], x["bar_index"]) for x in accepted], [(0, 4), (1, 0)])

    def test_momentum_baselines_use_closed_signal_bar_and_three_prior_closes(self):
        segment = bars([1.100, 1.101, 1.102, 1.103, 1.102, 1.101, 1.100, 1.099, 1.098, 1.097])
        cont = make_momentum_events([segment], fade=False)
        fade = make_momentum_events([segment], fade=True)
        at_three = next(x for x in cont if x["bar_index"] == 3)
        fade_at_three = next(x for x in fade if x["bar_index"] == 3)
        self.assertEqual(at_three["direction"], "CALL")
        self.assertEqual(fade_at_three["direction"], "PUT")

    def test_combined_frequency_and_wait_include_both_directions(self):
        rows = [
            {"outcome": "WIN", "signal_time": datetime(2026, 1, 5, 10, tzinfo=timezone.utc)},
            {"outcome": "LOSS", "signal_time": datetime(2026, 1, 5, 10, 5, tzinfo=timezone.utc)},
            {"outcome": "DRAW", "signal_time": datetime(2026, 1, 5, 10, 10, tzinfo=timezone.utc)},
        ]
        result = metrics(rows, bar_count=10)
        self.assertEqual(result["n"], 3)
        self.assertAlmostEqual(result["frequency"], 30.0)
        self.assertAlmostEqual(result["wait"], 70.0)
        self.assertAlmostEqual(result["net"], -0.08)

    def test_entry_is_next_open_and_settlement_is_horizon_close(self):
        segment = bars([1.100, 1.101, 1.102, 1.103, 1.102, 1.101, 1.100, 1.099])
        scored = score_events([self.event(1, direction="PUT")], [segment], horizon_bars=2)
        self.assertEqual(scored[0]["entry_time"], segment[2].timestamp)
        self.assertEqual(scored[0]["settle_time"], segment[3].timestamp + timedelta(minutes=5))
        self.assertEqual(scored[0]["outcome"], "LOSS")


if __name__ == "__main__":
    unittest.main()
