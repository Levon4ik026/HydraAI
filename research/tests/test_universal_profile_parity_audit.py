import sys
import unittest
from pathlib import Path

# The audit is also executable as a standalone research script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from universal_profile_parity_audit import format_candidate_row


class UniversalProfileParityReportTests(unittest.TestCase):
    def test_report_separates_builder_raw_from_eligible_raw_counts(self):
        row = format_candidate_row(
            cid="HYD-CAND-013",
            legacy_builder_raw_count=2271,
            legacy_eligible_raw_count=2241,
            engine_eligible_raw_count=2241,
            engine_accepted_count=2038,
            legacy_accepted_count=2038,
            raw_parity=True,
            accepted_parity=True,
            outcomes_ok=True,
        )
        self.assertEqual(
            row,
            "| HYD-CAND-013 | 2271 | 2241 | 2241 | 2038 | 2038 | PASS | PASS | PASS | PASS |",
        )

    def test_any_timestamp_or_outcome_mismatch_fails_candidate_row(self):
        row = format_candidate_row(
            cid="HYD-CAND-013",
            legacy_builder_raw_count=2271,
            legacy_eligible_raw_count=2241,
            engine_eligible_raw_count=2240,
            engine_accepted_count=2038,
            legacy_accepted_count=2038,
            raw_parity=False,
            accepted_parity=True,
            outcomes_ok=True,
        )
        self.assertIn("| FAIL | PASS | PASS | FAIL |", row)


if __name__ == "__main__":
    unittest.main()
