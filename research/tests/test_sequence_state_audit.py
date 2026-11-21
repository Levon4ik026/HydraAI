import unittest
from datetime import datetime,timedelta
from types import SimpleNamespace
from research.sequence_state_audit import sequence_states,orient
class Tests(unittest.TestCase):
 def bars(self,cs):
  return [SimpleNamespace(timestamp=datetime(2026,1,1)+timedelta(minutes=5*i),open=cs[i-1] if i else cs[i],high=max(cs[i-1] if i else cs[i],cs[i])+.1,low=min(cs[i-1] if i else cs[i],cs[i])-.1,close=cs[i]) for i in range(len(cs))]
 def test_up_path(self):
  r=sequence_states(self.bars([1,2,3,4,5,6,7,8]))[-1];self.assertEqual(r["flip_state_6"],"CALM_0_1");self.assertEqual(r["impulse_followthrough"],"CONTINUE");self.assertFalse(r["last_bar_reversal"])
 def test_alternating(self):self.assertEqual(sequence_states(self.bars([1,2,1,2,1,2,1,2]))[-1]["flip_state_6"],"CHAOTIC_4_5")
 def test_orientation(self):
  self.assertEqual(orient(2,"PUT"),-2);self.assertEqual(orient("LOWER_REJECTION","PUT"),"AGAINST_TRADE");self.assertEqual(orient("LOWER_REJECTION","CALL"),"WITH_TRADE")
if __name__=="__main__":unittest.main()
