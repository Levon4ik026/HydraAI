import unittest
from datetime import datetime, timedelta, timezone
from demo_execution_worker import market_rejection, signal_rejection, verification_rejection

class ExecutionGateTests(unittest.TestCase):
    def test_closed_market_is_blocked(self):
        self.assertIn("MARKET_CLOSED", market_rejection({"status":"MARKET_CLOSED","symbol":"EURUSD","active":False,"is_otc":False,"payout_ratio":.92,"timeframes_seconds":[300],"metadata_age_seconds":1},5))
    def test_payout_below_92_is_blocked(self):
        self.assertIn("LOW_PAYOUT", market_rejection({"status":"LOW_PAYOUT","symbol":"EURUSD","active":True,"is_otc":False,"payout_ratio":.50,"timeframes_seconds":[300],"metadata_age_seconds":1},5))
    def test_otc_is_blocked(self):
        self.assertIn("OTC", market_rejection({"status":"ACTIVE","symbol":"EURUSD","active":True,"is_otc":True,"payout_ratio":.95,"timeframes_seconds":[300],"metadata_age_seconds":1},5))
    def test_unavailable_expiry_is_blocked(self):
        self.assertIn("not offered", market_rejection({"status":"ACTIVE","symbol":"EURUSD","active":True,"is_otc":False,"payout_ratio":.95,"timeframes_seconds":[60,120,180,300],"metadata_age_seconds":1},30))
    def test_stale_live_tick_is_blocked(self):
        now=datetime.now(timezone.utc)
        self.assertIn("stale", signal_rejection({"tick_time":(now-timedelta(seconds=10)).isoformat(),"entry_time":now.isoformat()},now))

    def test_missing_order_verification_is_blocked(self):
        now = datetime.now(timezone.utc)
        self.assertIn("not VERIFIED", verification_rejection({"status":"PENDING"}, now))

    def test_only_closed_demo_eurusd_one_unit_five_minute_order_verifies(self):
        now = datetime.now(timezone.utc)
        record = {"status":"VERIFIED","verified_at_utc":now.isoformat(),"deal_id":"demo-123",
                  "asset":"EURUSD","is_demo":True,"closed":True,"amount":1,"expiry_seconds":300}
        self.assertIsNone(verification_rejection(record, now))
        record["is_demo"] = False
        self.assertIn("DEMO EURUSD", verification_rejection(record, now))

if __name__ == "__main__": unittest.main()
