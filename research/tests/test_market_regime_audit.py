import unittest
from research.market_regime_audit import classify_regimes, summarize

class MarketRegimeAuditTests(unittest.TestCase):
    def test_volatility_uses_only_prior_window(self):
        bars = [object() for _ in range(122)]
        feats = [{"atr14_close": 0.001, "adx14": 15.0, "ema20_50_atr": -0.2}
                 for _ in range(122)]
        feats[120]["atr14_close"] = 0.002
        states = classify_regimes(bars, feats)
        self.assertIsNone(states[119]["volatility"])
        self.assertEqual(states[120]["volatility"], "HIGH_VOL")
        self.assertEqual(states[120]["trend_strength"], "WEAK_ADX")
        self.assertEqual(states[120]["trend_bias"], "DOWN_BIAS")

    def test_fixed_adx_and_bias_bins(self):
        bars = [object() for _ in range(122)]
        feats = [{"atr14_close": 0.001, "adx14": 25.0, "ema20_50_atr": 0.1}
                 for _ in range(122)]
        states = classify_regimes(bars, feats)
        self.assertEqual(states[121]["trend_strength"], "MODERATE_ADX")
        self.assertEqual(states[121]["trend_bias"], "UP_BIAS")
        self.assertEqual(states[121]["regime"], "HIGH_VOL|MODERATE_ADX")

    def test_payout_accounting(self):
        result = summarize([{"outcome":"WIN"},{"outcome":"LOSS"},{"outcome":"DRAW"}])
        self.assertEqual(result[:4], (1,1,1,"50.0%"))
        self.assertAlmostEqual(result[4], -0.08)
        self.assertAlmostEqual(result[5], -0.08/3*100)

if __name__ == "__main__":
    unittest.main()
