import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'desktop'))
from tracking_core import ReadingGate, align_to_capture, remaining_at, estimate_send

class CoreTests(unittest.TestCase):
 def test_initial_single_requires_confirmation(self):
  gate=ReadingGate()
  self.assertEqual(gate.evaluate((350,3000),None,None,1,1,False).kind,'confirm')
  self.assertEqual(gate.evaluate((348,3000),None,None,6,1,False).kind,'accept')
 def test_initial_two_passes_immediate(self):
  self.assertEqual(ReadingGate().evaluate((350,3000),None,None,1,2,False).kind,'accept')
 def test_good_running_reading(self):
  self.assertEqual(ReadingGate().evaluate((290,3000),295,3000,10,1,True).kind,'accept')
 def test_new_tool_confirmed(self):
  gate=ReadingGate()
  self.assertEqual(gate.evaluate((2998,3000),270,3000,100,1,True).kind,'confirm')
  self.assertEqual(gate.evaluate((2993,3000),265,3000,105,1,True).kind,'new_tool')
 def test_noise_does_not_confirm_old_candidate(self):
  gate=ReadingGate();gate.evaluate((1400,3000),350,3000,100,1,True)
  self.assertEqual(gate.evaluate((330,3000),340,3000,105,1,True).kind,'accept')
  self.assertIsNone(gate.pending)
 def test_confirmation_expires(self):
  gate=ReadingGate();gate.evaluate((2900,3000),300,3000,1,1,True)
  self.assertEqual(gate.evaluate((2898,3000),250,3000,50,1,True).kind,'confirm')
 def test_timestamp_subtraction(self):
  self.assertAlmostEqual(align_to_capture(350,100,104.8,1.2),346.)
 def test_estimate_uses_live_not_cached(self):
  self.assertEqual(estimate_send(350,100,104.8,1.2,True),346)
 def test_clock_does_not_rewind(self):
  self.assertEqual(remaining_at(350,100,99,1,True),350)
 def test_pause_is_not_decremented(self):
  self.assertEqual(remaining_at(350,100,500,1,False),350)

if __name__=='__main__': unittest.main()
