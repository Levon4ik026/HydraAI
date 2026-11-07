import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from research.watch_frozen_put_candidate import load_or_create_state, newly_observed_settlements


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


    def test_v2_migration_preserves_boundary_but_not_legacy_cursor_or_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "hydra_put_forward_state.json"
            v2 = root / "hydra_put_forward_state_v2.json"
            legacy.write_text(json.dumps({
                "forward_start": "2026-11-07T13:35:00+00:00",
                "last_latest_m1_utc": "2026-11-07T13:44:00+00:00",
                "recorded_trade_keys": ["2026-11-07T13:35:00+00:00"],
            }), encoding="utf-8")
            state = load_or_create_state(v2, None, legacy_state_path=legacy)
            self.assertEqual(state["forward_start"], "2026-11-07T13:35:00+00:00")
            self.assertEqual(state["observation_integrity_version"], 1)
            self.assertIsNone(state["last_latest_m1_utc"])
            self.assertEqual(state["recorded_trade_keys"], [])

    def test_unversioned_v2_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps({
                "forward_start": "2026-11-07T13:35:00+00:00"
            }), encoding="utf-8")
            with self.assertRaises(SystemExit):
                load_or_create_state(path, None)


if __name__ == "__main__":
    unittest.main()
