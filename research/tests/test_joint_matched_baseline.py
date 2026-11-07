import unittest
from research.joint_matched_baseline import key, counts, wilson

class JointMatchedBaselineTests(unittest.TestCase):
    def test_joint_key_requires_all_causal_dimensions(self):
        self.assertEqual(key({"trend_bias":"UP_BIAS","volatility":"LOW_VOL","trend_strength":"WEAK_ADX"}),"UP_BIAS|LOW_VOL|WEAK_ADX")
        self.assertIsNone(key({"trend_bias":"UP_BIAS","volatility":None,"trend_strength":"WEAK_ADX"}))
    def test_directional_baseline_counts(self):
        rows=[{"up":True,"down":False,"draw":False},{"up":False,"down":True,"draw":False},{"up":False,"down":False,"draw":True}]
        self.assertEqual(counts(rows,"CALL"),(1,1,1))
        self.assertEqual(counts(rows,"PUT"),(1,1,1))
    def test_signal_counts(self):
        rows=[{"outcome":"WIN"},{"outcome":"LOSS"},{"outcome":"DRAW"}]
        self.assertEqual(counts(rows,"CALL"),(1,1,1))
    def test_wilson(self):
        lo,hi=wilson(8,10); self.assertLess(lo,.8); self.assertGreater(hi,.8)
        self.assertEqual(wilson(0,0),(None,None))

if __name__=="__main__": unittest.main()
