import unittest
from datetime import datetime, timedelta, timezone

from research.twenty_m_causal_edge_audit import classify_states, stats


class TwentyMinuteCausalAuditTests(unittest.TestCase):
    def test_classify_states_requires_full_prior_window(self):
        features = [{"atr14_close": 0.01, "adx14": 22, "ema20_50_atr": 0.2} for _ in range(121)]
        states = classify_states(features)
        self.assertIsNone(states[119])
        self.assertIsNotNone(states[120])
        self.assertEqual(states[120][0], "UP")

    def test_stats_uses_decisive_wr_and_92_percent_payout(self):
        rows = [
            {"outcome": "WIN", "net": 0.92, "direction": "CALL"},
            {"outcome": "LOSS", "net": -1.0, "direction": "CALL"},
            {"outcome": "DRAW", "net": 0.0, "direction": "PUT"},
        ]
        self.assertEqual(stats(rows), (3, 1, 1, 1, 50.0, -0.08))
        self.assertEqual(stats(rows, "CALL"), (2, 1, 1, 0, 50.0, -0.08))


if __name__ == "__main__":
    unittest.main()
