import unittest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from hydra_time_machine import (
    simulate_probabilities, tod_distance, trailing_vol, classify_vol,
    candidate_pool, MIN_POOL, score_forecasts,
)

class TimeMachineTests(unittest.TestCase):
    def test_tod_wraps_midnight(self):
        self.assertEqual(tod_distance(23*60+58, 2), 4)

    def test_fixed_seed_is_reproducible(self):
        bars=[]
        t=datetime(2026,1,1,tzinfo=timezone.utc)
        for i in range(20):
            p=1.1*(1+0.0001*i)
            bars.append(SimpleNamespace(open=p,close=p*1.0001,timestamp=t+timedelta(minutes=5*i)))
        pool=[(0,0,bars),(0,4,bars),(0,8,bars)]
        a=simulate_probabilities(pool,1.1,"CALL",3,123,simulations=500)
        b=simulate_probabilities(pool,1.1,"CALL",3,123,simulations=500)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a["p_win"]+a["p_loss"]+a["p_draw"],1.0)

    def test_trailing_vol_requires_history(self):
        bars=[SimpleNamespace(open=1,close=1+0.001*i) for i in range(13)]
        self.assertIsNone(trailing_vol(bars,11))
        self.assertIsNotNone(trailing_vol(bars,12))

    def test_probability_scores_exclude_draws(self):
        rows=[
            {"tm":0.8,"tod":0.6,"all":0.5,"actual":"WIN"},
            {"tm":0.3,"tod":0.4,"all":0.5,"actual":"LOSS"},
            {"tm":0.99,"tod":0.99,"all":0.99,"actual":"DRAW"},
        ]
        scored=score_forecasts(rows)
        self.assertEqual([row[1] for row in scored],[2,2,2])
        self.assertAlmostEqual(scored[0][2],((0.8-1)**2+(0.3-0)**2)/2)

    def test_volatility_tercile(self):
        values=list(range(30))
        self.assertEqual(classify_vol(0.1,values),0)
        self.assertEqual(classify_vol(29,values),2)
        self.assertIsNone(classify_vol(1,values[:5]))

    def test_pool_never_uses_future_bars(self):
        t=datetime(2026,1,2,12,0,tzinfo=timezone.utc)
        bars=[]
        for i in range(80):
            p=1.1+0.00001*i
            bars.append(SimpleNamespace(timestamp=t-timedelta(minutes=5*(80-i)),open=p,high=p,low=p,close=p+0.00001))
        pool,_=candidate_pool([bars],t,0.000001,3)
        self.assertTrue(all(bars[j+2].timestamp<t for _,j,_ in pool))

if __name__=="__main__":
    unittest.main()
