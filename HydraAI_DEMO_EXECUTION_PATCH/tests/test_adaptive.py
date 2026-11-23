import unittest

from hydra_demo.adaptive import CandidateStats, Regime, select_candidate


class AdaptiveSelectorTests(unittest.TestCase):
    def test_candidate_is_selected_only_in_its_forward_validated_regime(self):
        stats = [
            CandidateStats("CAND-012", "TREND", wins=90, losses=10,
                           max_drawdown_units=2.0, payout=0.92),
        ]
        selected, _ = select_candidate(
            Regime("TREND", 0.8, "test"), stats, payout=0.92, min_trades=100
        )
        self.assertEqual(selected, "CAND-012")

        selected, reason = select_candidate(
            Regime("RANGE", 0.8, "test"), stats, payout=0.92, min_trades=100
        )
        self.assertIsNone(selected)
        self.assertIn("no candidate", reason)

    def test_candidate_waits_until_100_forward_outcomes(self):
        stats = [
            CandidateStats("CAND-012", "TREND", wins=89, losses=10,
                           max_drawdown_units=2.0, payout=0.92),
        ]
        selected, reason = select_candidate(
            Regime("TREND", 0.8, "test"), stats, payout=0.92, min_trades=100
        )
        self.assertIsNone(selected)
        self.assertIn(">= 100 forward trades", reason)


if __name__ == "__main__":
    unittest.main()
