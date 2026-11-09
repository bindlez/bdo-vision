import sys,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from auto_craft import CraftInference,identify,forecast,families
from craft_economy import craft_spec

CONTEXT={'active':True,'tool':'tool1','kind':'alchemy','verified':3000,'remaining':2990,'speed':1}
ITEM='Elixir of Demihuman Hunt'
QUOTES={p['name']:{'unit_price':100,'source':'Test market'} for p in craft_spec()['items'].values()}


class AutoCraftTests(unittest.TestCase):
    def detected(self):
        e=CraftInference();e.tick(CONTEXT,True,0)
        self.assertFalse(e.observe(1,ITEM,4,CONTEXT,0));e.tick(CONTEXT,True,1)
        self.assertTrue(e.observe(2,ITEM,4,CONTEXT,1));return e

    def test_repeated_output_detects_without_manual_recipe_and_never_guesses_ambiguity(self):
        e=self.detected();d=e.snapshot(CONTEXT,QUOTES,True)
        self.assertEqual(d['recipe'],ITEM);self.assertEqual(d['recordedValue'],800);self.assertIsNone(d['recordedPerHour'])
        self.assertEqual(d['model']['toolValue'],d['model']['perBatch']*3000)
        self.assertEqual(d['remainingValue'],d['model']['perBatch']*2990)
        e.observe(2,ITEM,4,CONTEXT,1);self.assertEqual(e.run['counts'][ITEM],8)
        with patch('auto_craft.families',return_value=({}, {('alchemy',ITEM.casefold()):{'a','b'}})):self.assertIsNone(identify(ITEM,'alchemy'))
        self.assertIsNone(identify(ITEM,'cooking'))

    def test_same_frame_is_not_two_witnesses_and_tool_context_is_required(self):
        e=CraftInference();e.observe(1,ITEM,4,CONTEXT,0);e.observe(2,ITEM,4,CONTEXT,0)
        self.assertIsNone(e.run);e.observe(3,ITEM,4,CONTEXT,1);self.assertIsNotNone(e.run)
        e=CraftInference();self.assertFalse(e.observe(1,ITEM,4,None,0));self.assertFalse(e.observe(2,ITEM,4,{**CONTEXT,'active':False},1))

    def test_observed_rates_pause_without_inventing_drops_and_projection_is_distinct(self):
        e=self.detected()
        for second in range(2,62):e.tick(CONTEXT,True,second)
        d=e.snapshot(CONTEXT,QUOTES,True);self.assertEqual(d['observedSeconds'],61);self.assertAlmostEqual(d['recordedPerHour'],800*3600/61)
        e.tick(CONTEXT,False,62);e.tick(CONTEXT,False,102);e.tick(CONTEXT,True,103)
        self.assertEqual(e.run['observed'],61);self.assertEqual(e.run['counts'][ITEM],8)
        self.assertEqual(e.snapshot(CONTEXT,QUOTES,False)['model']['toolValue'],d['model']['toolValue'])
        self.assertFalse(e.snapshot({**CONTEXT,'tool':'nextTool'},QUOTES,True)['current'])

    def test_rate_uses_ten_visible_seconds_including_startup_before_first_drop(self):
        e=CraftInference()
        for second in range(8):e.tick(CONTEXT,True,second)
        e.observe(1,ITEM,4,CONTEXT,7)
        e.tick(CONTEXT,True,8)
        e.observe(2,ITEM,4,CONTEXT,8)
        e.tick(CONTEXT,True,9)
        self.assertIsNone(e.snapshot(CONTEXT,QUOTES,True)['recordedPerHour'])
        e.tick(CONTEXT,True,10)
        e.tick(CONTEXT,False,11)
        e.tick(CONTEXT,False,35)
        data=e.snapshot(CONTEXT,QUOTES,False)
        self.assertEqual(data['observedSeconds'],10)
        self.assertEqual(data['recordedPerHour'],288000)

    def test_rare_output_maps_to_parent_unknown_prices_stay_unknown_and_byproducts_kept(self):
        family=identify(ITEM,'alchemy');spec=craft_spec();rare=spec['items'][str(family['recipes'][0]['rare']['itemId'])]['name']
        self.assertEqual(identify(rare,'alchemy')['key'],family['key'])
        e=CraftInference();e.observe(1,rare,1,CONTEXT,0);e.observe(2,rare,1,CONTEXT,1)
        byproduct=spec['items'][str(spec['byproducts']['alchemy']['id'])]['name'];e.observe(3,byproduct,5,CONTEXT,2)
        d=e.snapshot(CONTEXT,QUOTES,True);self.assertEqual(d['recordedValue'],200);self.assertFalse(d['unpriced'])
        self.assertIsNone(e.snapshot(CONTEXT,{},True)['model']['toolValue'])
        e=CraftInference();e.observe(1,ITEM,4,CONTEXT,0)
        self.assertFalse(e.observe(2,byproduct,5,CONTEXT,.2));self.assertIsNone(e.run)
        e.observe(3,ITEM,4,CONTEXT,1);self.assertEqual(e.run['counts'][byproduct],5);self.assertIn(2,e.run['ids'])

    def test_recipe_changes_restart_forecast_and_retained_state_cannot_resume_on_restart(self):
        e=self.detected();other=next(g['name'] for g in families()[0].values() if g['kind']=='alchemy' and g['name']!=ITEM and identify(g['name'],'alchemy'))
        e.observe(3,other,2,CONTEXT,2);e.tick(CONTEXT,True,3);e.observe(4,other,2,CONTEXT,3)
        self.assertTrue(e.run['changedRecipe']);self.assertEqual(e.run['actions'],2990)
        restored=CraftInference(json.loads(json.dumps(e.run)))
        self.assertIsNone(restored.snapshot(None,QUOTES,False)['model'])


if __name__=='__main__':unittest.main()
