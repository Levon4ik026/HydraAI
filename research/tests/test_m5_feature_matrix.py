import unittest
from datetime import datetime, timedelta, timezone

from research.build_m5_feature_matrix import build_rows, ema, rsi_wilder
from research.reproduce_m5_bb_williams_adx import Bar


class M5FeatureMatrixTests(unittest.TestCase):
    def make_bars(self, n=180):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        out = []
        price = 1.10
        for i in range(n):
            # Deterministic non-flat path with a small repeating range.
            drift = 0.00003 if (i // 12) % 2 == 0 else -0.00002
            o = price
            c = o + drift + (0.00001 if i % 3 else -0.000005)
            h = max(o, c) + 0.00004
            l = min(o, c) - 0.00003
            out.append(Bar(start + timedelta(minutes=5*i), o, h, l, c))
            price = c
        return out

    def test_ema_and_rsi_warmup_are_explicit(self):
        values = [float(i + 1) for i in range(30)]
        e = ema(values, 20)
        r = rsi_wilder(values, 14)
        self.assertTrue(all(x is None for x in e[:19]))
        self.assertIsNotNone(e[19])
        self.assertTrue(all(x is None for x in r[:14]))
        self.assertEqual(r[14], 100.0)

    def test_prior_day_and_week_levels_are_previous_period_only(self):
        bars = self.make_bars(600)
        rows = list(build_rows([bars]))
        # Jan 6 is the second UTC day in this synthetic series.
        idx = next(i for i, b in enumerate(bars) if b.timestamp.date().isoformat() == "2026-01-06")
        previous_day = bars[:idx]
        self.assertAlmostEqual(rows[idx]["previous_observed_utc_day_high"],
                               max(b.high for b in previous_day))
        self.assertAlmostEqual(rows[idx]["previous_observed_utc_day_low"],
                               min(b.low for b in previous_day))
        # A future extension inside the current period cannot rewrite prior-period levels.
        changed = list(bars)
        b = changed[-1]
        changed[-1] = Bar(b.timestamp, b.open, b.high + 0.01, b.low, b.close)
        extended = list(build_rows([changed]))
        self.assertEqual(rows[idx]["previous_observed_utc_day_high"],
                         extended[idx]["previous_observed_utc_day_high"])

    def test_future_bars_do_not_change_prior_feature_rows(self):
        bars = self.make_bars(180)
        full = list(build_rows([bars]))
        cut = 130
        prefix = list(build_rows([bars[:cut]]))
        keys = (
            "ema20", "ema50", "rsi14", "adx14", "atr14",
            "atr_pct_rank_prior120", "return6_atr", "body_range",
            "previous_observed_utc_day_high", "previous_observed_utc_week_low",
        )
        for key in keys:
            self.assertEqual(full[cut - 1][key], prefix[cut - 1][key], key)

    def test_matrix_row_count_and_segment_boundaries(self):
        bars = self.make_bars(100)
        rows = list(build_rows([bars[:50], bars[50:]]))
        self.assertEqual(len(rows), 100)
        self.assertEqual(rows[49]["segment_id"], 0)
        self.assertEqual(rows[50]["segment_id"], 1)
        self.assertEqual(rows[50]["bar_index"], 0)
        self.assertIsNone(rows[50]["atr14"])


if __name__ == "__main__":
    unittest.main()
