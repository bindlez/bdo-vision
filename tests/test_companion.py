import json,sys,unittest,tkinter as tk,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from inventory_reader import parse_weight
from grind_identity import infer,pursuits,session_label
from craft_panel_contract import validate_reply
from app import App
from planner_bridge import PlannerBridge


class CompanionRules(unittest.TestCase):
    def test_inventory_weight_requires_visible_inventory_and_strict_numbers(self):
        self.assertEqual(parse_weight('Inventory\nWeight 2,452.65 / 3,538 LT'),{'current':2452.65,'maximum':3538})
        self.assertEqual(parse_weight('Inventory Weight == 2,465.8 /3,538LT +'),{'current':2465.8,'maximum':3538.})
        for raw in ('Weight 100/3000 LT','Inventory\nTool 382/3000','Inventory Weight 2,45/3000 LT','Inventory Weight -2/3000 LT','Inventory Weight 2/0 LT'):
            self.assertIsNone(parse_weight(raw),raw)

    def test_spot_identity_never_uses_shared_rare_items_as_location_proof(self):
        self.assertIsNone(infer(["Kabua's Artifact",'Black Stone'])['spot'])
        self.assertEqual(infer(['Tungrad Ruins Fragment'])['spot'],'Tungrad Ruins')
        self.assertTrue(infer(['Tungrad Ruins Fragment','Corrupt Power Source'])['ambiguous'])
        self.assertIn("Lafi Bedmountain's Upgraded Telescope Parts",pursuits('Tungrad Ruins'))
        self.assertTrue(session_label().startswith('Grind · '))

    def test_native_reply_rejects_nonfinite_and_stale_recipe(self):
        self.assertEqual(validate_reply({'error':'bad input'},'r'),{'error':'bad input'})
        with self.assertRaises(ValueError):validate_reply({'recipe':'wrong'},'r')
        with self.assertRaises(ValueError):validate_reply({'recipe':'r','batches':float('nan')},'r')


class CompanionIntegration(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        with patch.object(App,'start_bridge'):self.app=App(self.root)
        self.bridge=self.app.bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,))
    def tearDown(self):self.app.close()

    def test_search_and_request_are_local_until_shared_engine_replies(self):
        panel=self.app.loot.grind.live.craft_panel
        with patch('game_overlay.OverlaySurface.show',return_value=True):panel.open()
        panel.search.set('Nurungji');self.assertTrue(panel.matches)
        panel.results.selection_set(0);panel.choose()
        for key,value in {'maximum':'100','current':'0','tool':'100','reserve':'0'}.items():panel.fields[key].set(value)
        panel.calculate();self.assertIsNotNone(panel.request)
        with self.bridge._lock:q=dict(self.bridge.craft_panel_request)
        self.assertEqual(q['recipe'],panel.recipe['id']);self.assertFalse(q['start'])
        with urllib.request.urlopen(self.bridge.base_url+'/durability') as response:reading=json.load(response)
        self.assertEqual(reading['craft_panel_request']['id'],q['id']);self.assertNotIn('crafting_loot',reading)
        payload={'id':q['id'],'instance_id':self.bridge.instance_id,'result':{'error':'Enter verified weight'}}
        request=urllib.request.Request(self.bridge.base_url+'/craft-panel-result',json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:self.assertEqual(response.status,200)
        panel.refresh();self.assertIn('Enter verified weight',panel.status.cget('text'))
        payload['id']='stale'
        request=urllib.request.Request(self.bridge.base_url+'/craft-panel-result',json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request)
        panel.close();self.assertIsNone(panel.surface)

    def test_auto_spot_persists_without_renaming_the_session_or_inventing_treasure(self):
        g=self.app.loot.grind;g.start();s=g.insights.session;name=s.history()[0]['label']
        g.observe_spot('Corrupt Power Source')
        self.assertEqual(s.db.execute('SELECT spot FROM grind_details WHERE session=?',(s.id,)).fetchone()[0],'Yzrahid Highlands')
        self.assertEqual(s.history()[0]['label'],name);self.assertEqual(g.target.get(),'')
        g.observe_spot('Tungrad Ruins Fragment');self.assertIn('Ambiguous',g.spot.get())
        g.spot.set('Tungrad Ruins');g.spot_override();self.assertFalse(g.auto_spot)
        g.observe_spot('Corrupt Power Source');self.assertEqual(g.spot.get(),'Tungrad Ruins')

    def test_event_stream_delivers_without_polling_and_keeps_same_origin_policy(self):
        with urllib.request.urlopen(self.bridge.base_url+'/craft-panel-events',timeout=2) as response:
            self.assertEqual(response.headers['Content-Type'],'text/event-stream')
            self.assertIsNone(json.loads(response.readline().decode()[6:])['craft_panel_request']);response.readline()
            from craft_economy import recipes
            ident=next(r['id'] for r in recipes() if r['type']=='cooking')
            request_id=self.bridge.request_craft_panel({'recipe':ident})
            event=json.loads(response.readline().decode()[6:]);self.assertEqual(event['craft_panel_request']['id'],request_id)
        request=urllib.request.Request(self.bridge.base_url+'/craft-panel-events',headers={'Origin':'https://foreign.example'})
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(request)

    def test_lite_use_never_launches_inventory_ocr(self):
        self.app.lite_use.set(True)
        with patch('inventory_reader.ImageGrab.grab') as capture:self.app.inventory.read();capture.assert_not_called()
        self.assertEqual(self.app.inventory.snapshot,{})

    def test_fairy_catalog_and_extra_cp_charts_use_existing_records(self):
        self.app.open_fairy_desktop();view=self.app.fairy_desktop
        self.assertEqual(len(view.tree.get_children()),12);self.assertIn('No recognized',view.loot.get())
        self.app.loot.open();cp=self.app.loot.cp_info
        cp.chart_mode.set('Byproduct EXP mix');cp.draw_chart();self.assertTrue(cp.chart.find_all())


if __name__=='__main__':unittest.main()
