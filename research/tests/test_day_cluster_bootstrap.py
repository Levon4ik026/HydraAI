import unittest

from research.day_cluster_bootstrap import bootstrap


def row(day, outcome):
    return {"signal_time": day + "T12:00:00+00:00", "outcome": outcome}


class DayClusterBootstrapTests(unittest.TestCase):
    def test_bootstrap_is_reproducible(self):
        base = [row("2026-10-01", "WIN"), row("2026-10-02", "LOSS")]
        filtered = [row("2026-10-01", "LOSS"), row("2026-10-02", "LOSS")]
        a = bootstrap(base, filtered, replicates=1000, seed=7)
        b = bootstrap(base, filtered, replicates=1000, seed=7)
        self.assertEqual(a, b)

    def test_paired_delta_reflects_filter_minus_base(self):
        base = [row("2026-10-01", "WIN"), row("2026-10-02", "LOSS")]
        filtered = [row("2026-10-01", "LOSS")]
        result = bootstrap(base, filtered, replicates=1000, seed=11)
        lo, hi = result["delta_net_ci"]
        # On day one the filter loses instead of winning; on day two it matches base.
        self.assertLessEqual(hi, 0.0)

    def test_requires_multiple_signal_days(self):
        with self.assertRaises(ValueError):
            bootstrap([row("2026-10-01", "WIN")], [], replicates=1000)


if __name__ == "__main__":
    unittest.main()
