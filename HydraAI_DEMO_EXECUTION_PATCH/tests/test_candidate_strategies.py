from datetime import datetime, timedelta, timezone
import unittest

from hydra_demo.engine import Candle, candidate_signals


class CandidateStrategyTests(unittest.TestCase):
    def test_cand012_bearish_cross_uses_approved_inverse_call(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        m1 = []
        previous = 1.1000
        closes = []
        for i in range(80):
            if i < 55:
                target = 1.1000 + i * 0.00005
            else:
                target = 1.1000 + 54 * 0.00005 - (i - 54) * 0.00015
            closes.append(target)

        for block, target in enumerate(closes):
            block_open = previous
            for minute in range(5):
                next_price = block_open + (target - block_open) * (minute + 1) / 5
                candle_open = block_open + (target - block_open) * minute / 5
                ts = start + timedelta(minutes=block * 5 + minute)
                m1.append(Candle(
                    timestamp=ts,
                    open=candle_open,
                    high=max(candle_open, next_price) + 0.00001,
                    low=min(candle_open, next_price) - 0.00001,
                    close=next_price,
                ))
            previous = target

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-012"]
        self.assertTrue(signals, "synthetic trend reversal should produce a CAND-012 signal")
        self.assertTrue(all(s.direction == "CALL" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 5 for s in signals))

    def test_cand010_previous_day_low_breakdown_is_put_60m(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        m1 = []
        price = 1.1000
        total_minutes = 2 * 24 * 60
        breakout_minute = 24 * 60 + 5 * 60
        for minute in range(total_minutes):
            ts = start + timedelta(minutes=minute)
            op = price
            if minute < 24 * 60:
                # Previous UTC day: fixed low is 1.0990.
                close = 1.1000
                low = 1.0990
                high = 1.1010
            elif minute < breakout_minute:
                close = 1.1000
                low = 1.0995
                high = 1.1005
            elif minute < breakout_minute + 5:
                # One completed M5 candle closes through yesterday's low.
                close = 1.0985
                low = min(op, close) - 0.0001
                high = max(op, close) + 0.0001
            else:
                close = 1.0985
                low = 1.0983
                high = 1.0987
            m1.append(Candle(ts, op, high, low, close))
            price = close

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-010"]
        self.assertTrue(signals, "a completed M5 close below the prior UTC-day low must signal")
        self.assertTrue(all(s.direction == "PUT" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 60 for s in signals))


if __name__ == "__main__":
    unittest.main()
