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


    def test_cand001_overbought_bearish_m5_uses_put_5m(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        m1 = []
        price = 1.1000
        blocks = 160
        for block in range(blocks):
            op = price
            close = 1.1000 + block * 0.00002
            if block == blocks - 1:
                close = op - 0.00001  # bearish body, but RSI remains overbought
            for minute in range(5):
                a = op + (close - op) * minute / 5
                b = op + (close - op) * (minute + 1) / 5
                ts = start + timedelta(minutes=block * 5 + minute)
                high = max(a, b) + 0.000005
                low = min(a, b) - 0.000005
                if block == blocks - 1 and minute == 0:
                    high = op + 0.001
                    low = op - 0.001
                m1.append(Candle(ts, a, high, low, b))
            price = close
        entry_time = start + timedelta(minutes=blocks * 5)
        m1.append(Candle(entry_time, price, price + 0.00001, price - 0.00001, price))

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-001"]
        self.assertTrue(signals, "overbought bearish M5 with elevated ATR should signal")
        self.assertTrue(all(s.direction == "PUT" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 5 for s in signals))

    def test_cand008_weekly_low_sweep_reclaim_uses_approved_put_30m(self):
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)  # Monday 00:00 UTC
        m1 = []
        total_minutes = 7 * 24 * 60 + 6
        price = 1.1000
        for minute in range(total_minutes):
            ts = start + timedelta(minutes=minute)
            op = price
            if minute == 100:
                low, close, high = 1.0990, 1.1000, 1.1002
            elif 7 * 24 * 60 <= minute < 7 * 24 * 60 + 5:
                low, close, high = 1.0985, 1.1002, 1.1003
            else:
                low, close, high = 1.0998, 1.1000, 1.1002
            m1.append(Candle(ts, op, high, low, close))
            price = close

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-008"]
        self.assertTrue(signals, "weekly low sweep and bullish reclaim should signal")
        self.assertTrue(all(s.direction == "PUT" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 30 for s in signals))

    def test_cand014_ny_downside_shock_rebound_uses_call_30m(self):
        from zoneinfo import ZoneInfo

        ny = ZoneInfo("America/New_York")
        first_session_date = datetime(2026, 1, 1, tzinfo=ny).date()
        m1 = []
        price = 1.1000
        for session_index in range(21):
            session_date = first_session_date + timedelta(days=session_index)
            session_start = datetime.combine(session_date, datetime.min.time(), ny).replace(hour=18)
            log_return = -0.005 if session_index == 20 else 0.0001
            per_minute = log_return / 1380
            for minute in range(1380):
                ts = session_start + timedelta(minutes=minute)
                op = price
                close = op * __import__("math").exp(per_minute)
                m1.append(Candle(ts.astimezone(timezone.utc), op,
                                 max(op, close) * 1.000001,
                                 min(op, close) * 0.999999, close))
                price = close
        # First M1 candle of the next NY 18:00 session is the entry reference.
        next_start = datetime.combine(
            first_session_date + timedelta(days=21), datetime.min.time(), ny
        ).replace(hour=18)
        m1.append(Candle(next_start.astimezone(timezone.utc), price,
                         price * 1.00001, price * 0.99999, price))

        signals = [s for s in candidate_signals(m1) if s.candidate_id == "CAND-014"]
        self.assertTrue(signals, "a downside shock beyond the prior-20-session threshold should signal")
        self.assertTrue(all(s.direction == "CALL" for s in signals))
        self.assertTrue(all(s.expiry_minutes == 30 for s in signals))


if __name__ == "__main__":
    unittest.main()
