import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from craft_dashboard import profit_breakdown
class ProfitTests(unittest.TestCase):
 def test_costs_and_tax(self):
  self.assertIn('550',profit_breakdown(1000,200,80,50))
 def test_unknown_and_invalid_are_not_zero(self):
  for args in [(1000,'',80,0),(1000,0,101,0),(1000,0,'NaN',0),(None,0,100,0),(1000,0,100,0,1)]:
   self.assertNotIn('MODELED PROFIT:',profit_breakdown(*args))
