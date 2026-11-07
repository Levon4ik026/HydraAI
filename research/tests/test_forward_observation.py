import unittest
from datetime import datetime, timedelta, timezone

from research.watch_frozen_put_candidate import newly_observed_settlements


class ForwardObservationTests(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime(2026, 11, 7, 13, 38, tzinfo=timezone.utc)

    def trade(self, settlement_minutes):
        return {"settlement_time": self.t0 + timedelta(minutes=settlement_minutes)}

    def test_scores_only_settlements_in_newly_observed_minute(self):
        trades = [self.trade(1), self.trade(2), self.trade(3)]
        selected = newly_observed_settlements(trades, self.t0, self.t0 + timedelta(minutes=1))
        self.assertEqual(selected, [self.trade(2)])

    def test_first_snapshot_never_replays_history(self):
        self.assertEqual(newly_observed_settlements([self.trade(2)], None, self.t0), [])

    def test_unchanged_timestamp_never_scores(self):
        self.assertEqual(
            newly_observed_settlements([self.trade(1)], self.t0, self.t0), []
        )

    def test_reconnect_jump_is_quarantined(self):
        self.assertEqual(
            newly_observed_settlements(
                [self.trade(2), self.trade(3)],
                self.t0,
                self.t0 + timedelta(minutes=3),
            ),
            [],
        )

    def test_rollback_is_quarantined(self):
        self.assertEqual(
            newly_observed_settlements(
                [self.trade(1)],
                self.t0,
                self.t0 - timedelta(minutes=1),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
