import unittest

from research.win_loss_feature_audit import (
    benjamini_hochberg, mann_whitney_p, cliff_delta, average_ranks,
)


class WinLossFeatureAuditTests(unittest.TestCase):
    def test_average_ranks_handles_ties(self):
        self.assertEqual(average_ranks([3.0, 1.0, 1.0, 4.0]), [3.0, 1.5, 1.5, 4.0])

    def test_mann_whitney_identical_samples_is_not_significant(self):
        p = mann_whitney_p([1, 2, 3, 4], [1, 2, 3, 4])
        self.assertIsNotNone(p)
        self.assertGreater(p, 0.5)

    def test_mann_whitney_separates_ordered_samples(self):
        p = mann_whitney_p([8, 9, 10, 11, 12], [1, 2, 3, 4, 5])
        self.assertLess(p, 0.05)

    def test_cliff_delta_direction(self):
        self.assertEqual(cliff_delta([3, 4], [1, 2]), 1.0)
        self.assertEqual(cliff_delta([1, 2], [3, 4]), -1.0)

    def test_bh_is_monotone_in_sorted_p_values(self):
        q = benjamini_hochberg([("a", 0.01), ("b", 0.04), ("c", 0.03)])
        self.assertAlmostEqual(q["a"], 0.03)
        self.assertAlmostEqual(q["c"], 0.045)
        self.assertAlmostEqual(q["b"], 0.045)

    def test_bh_preserves_missing(self):
        q = benjamini_hochberg([("a", None), ("b", 0.2)])
        self.assertIsNone(q["a"])
        self.assertEqual(q["b"], 0.2)


if __name__ == "__main__":
    unittest.main()
