import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'desktop'))
from tracking_core import CraftPhase, ReadingGate, align_to_capture, craft_run_state, remaining_at, estimate_send,replacement_needs_use

class CoreTests(unittest.TestCase):
 def test_craft_state_keeps_timer_during_verification_and_estimate(self):
  inputs=dict(session='run',remaining=None,running=False,detailed=True,lite=False,estimate=False,verifying=False,tool=None)
  def state(**updates):return craft_run_state(**(inputs|updates))
  self.assertIs(state().phase,CraftPhase.WAITING)
  self.assertIs(state(verifying=True).phase,CraftPhase.VERIFYING)
  tracking=state(remaining=30,running=True,tool={'id':'tool'})
  self.assertIs(tracking.phase,CraftPhase.TRACKING);self.assertTrue(tracking.show_on_dock(True))
  gap=state(remaining=28,running=True,estimate=True)
  self.assertIs(gap.phase,CraftPhase.ESTIMATING);self.assertTrue(gap.estimate_quest)
  self.assertEqual(gap.session,tracking.session)
  self.assertIs(state(remaining=28).phase,CraftPhase.PAUSED)
  self.assertIs(state(remaining=0,running=True).phase,CraftPhase.FINISHED)
 def test_exhausting_tool_cannot_reset_to_full_neighbor_by_position(self):
  self.assertTrue(replacement_needs_use('old:0','misread:0',382,83,3000,0))
  for remaining in (5,4,3,0):
   self.assertTrue(replacement_needs_use('old:0','neighbor:0',remaining,2993,3000,0))
   self.assertTrue(replacement_needs_use('old:0','neighbor:0',remaining,2992,3000,1))
 def test_real_replacement_and_explicit_scan_are_allowed(self):
  self.assertFalse(replacement_needs_use('old:0','new:0',3,2993,3000,2))
  self.assertFalse(replacement_needs_use('old:0','new:0',3,2993,3000,0,manual=True))
  self.assertFalse(replacement_needs_use(None,'new:0',0,2993,3000,0))
  self.assertFalse(replacement_needs_use('old:0','old:0',3,2,3000,2))
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
