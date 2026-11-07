import math
import unittest

from research.statistical_validation import (
    binomial_upper_tail, summarize_fixed_payout, wilson_interval,
)


class StatisticalValidationTests(unittest.TestCase):
    def test_wilson_known_small_sample(self):
        low, high = wilson_interval(15, 20)
        self.assertAlmostEqual(low, 0.5313, places=3)
        self.assertAlmostEqual(high, 0.863, places=3)

    def test_empty_sample(self):
        self.assertIsNone(wilson_interval(0, 0))
        self.assertIsNone(binomial_upper_tail(0, 0, 0.5))
        result = summarize_fixed_payout(0, 0, 0)
        self.assertIsNone(result["win_rate"])
        self.assertIsNone(result["binomial_p_value_one_sided_iid_assumption"])

    def test_binomial_boundaries(self):
        self.assertEqual(binomial_upper_tail(0, 10, 0.5), 1.0)
        self.assertEqual(binomial_upper_tail(1, 10, 0.0), 0.0)
        self.assertEqual(binomial_upper_tail(10, 10, 1.0), 1.0)

    def test_binomial_matches_small_exact_case(self):
        # P[X >= 2] for n=3, p=0.5 = 0.5.
        self.assertAlmostEqual(binomial_upper_tail(2, 3, 0.5), 0.5)

    def test_fixed_92_percent_economics(self):
        result = summarize_fixed_payout(53, 47, 2, payout=0.92)
        self.assertAlmostEqual(result["break_even_win_rate"], 1 / 1.92)
        self.assertAlmostEqual(result["net_profit_units"], 1.76)
        self.assertEqual(result["trades"], 102)
        self.assertEqual(result["decisive_trades"], 100)

    def test_draws_do_not_enter_win_rate(self):
        result = summarize_fixed_payout(60, 40, 25, payout=0.92)
        self.assertEqual(result["win_rate"], 0.6)
        self.assertEqual(result["trades"], 125)

    def test_invalid_counts_and_rates_rejected(self):
        for args in [(-1, 2, 0), (1.5, 2, 0), (3, 2, 0)]:
            with self.assertRaises(ValueError):
                summarize_fixed_payout(*args)
        with self.assertRaises(ValueError):
            wilson_interval(2, 1)
        with self.assertRaises(ValueError):
            binomial_upper_tail(1, 2, 1.1)

    def test_p_value_is_bounded(self):
        p = binomial_upper_tail(60, 100, 1 / 1.92)
        self.assertTrue(0 <= p <= 1)
        self.assertTrue(math.isfinite(p))


if __name__ == "__main__":
    unittest.main()
