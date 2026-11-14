import unittest
from datetime import datetime, timedelta, timezone
from research.loss_context_audit import context_rows
from research.reproduce_m5_bb_williams_adx import Bar


class LossContextAuditTests(unittest.TestCase):
    def make_bars(self, closes):
        out = []
        for i, close in enumerate(closes):
            open_ = closes[i-1] if i else close
            high = max(open_, close) + 0.5
            low = min(open_, close) - 0.5
            out.append(Bar(datetime(2026, 1, 1, tzinfo=timezone.utc)+timedelta(minutes=5*i),
                           open_, high, low, close))
        return out

    def test_context_uses_only_past_and_current_candles(self):
        bars = self.make_bars([10+i*0.1 for i in range(20)])
        rows = context_rows(bars)
        changed_future = bars[:]
        changed_future[19] = Bar(changed_future[19].timestamp, 1, 2, 0.5, 1.5)
        rows2 = context_rows(changed_future)
        for key in rows[15]:
            self.assertEqual(rows[15][key], rows2[15][key])

    def test_efficiency_is_bounded(self):
        bars = self.make_bars([10, 11, 10, 12, 11, 13, 12, 14, 13, 15, 14, 16, 15, 17])
        row = context_rows(bars)[-1]
        self.assertGreaterEqual(row["efficiency_6"], 0)
        self.assertLessEqual(row["efficiency_6"], 1)

    def test_close_location_is_bounded(self):
        bars = self.make_bars([10+i*0.2 for i in range(4)])
        for row in context_rows(bars):
            if row["close_location"] is not None:
                self.assertGreaterEqual(row["close_location"], 0)
                self.assertLessEqual(row["close_location"], 1)


if __name__ == "__main__":
    unittest.main()
