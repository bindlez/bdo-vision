import json
import sys
import tempfile
import time
import tkinter as tk
import types
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from silver_loot import silver_snapshot
from planner_bridge import PlannerBridge
from loot_ui import LootTracker


class SilverLootTests(unittest.TestCase):
    def test_totals_preserve_unknown_values(self):
        rows=[(1,'','Elixir of Demihuman Hunt',4,'','s','Crafted'),(2,'','Shining Powder',1,'','s','Rare craft'),(3,'','Unpriced',2,'','s','Crafted')]
        prices={'Elixir of Demihuman Hunt':{'unit_price':100,'source':'Central Market'},'Shining Powder':{'unit_price':20,'source':'Central Market'}}
        result=silver_snapshot(rows,prices)
        self.assertEqual(result['market_silver'],420)
        self.assertEqual(result['elixir_units'],4);self.assertEqual(result['extra_units'],3)
        self.assertEqual(result['rare_units'],1);self.assertEqual(result['unpriced_types'],1)
        self.assertIsNone(silver_snapshot(rows,{})['market_silver'])

    def test_bridge_optional_snapshot_and_clearing(self):
        html=Path(__file__).resolve().parents[1]/'bdo-market-intelligence.html'
        bridge=PlannerBridge(html,ports=(7385,))
        try:
            self.assertNotIn('crafting_loot',bridge.send(10,3000,1))
            snapshot={'available':False,'reason':'Game in tray','elixir_units':12,'items':[{'item':'Elixir','quantity':12}]}
            bridge.send(9,3000,1,crafting_loot=snapshot);snapshot['items'][0]['quantity']=999
            with urllib.request.urlopen(bridge.base_url+'/durability') as response:data=json.load(response)
            self.assertEqual(data['crafting_loot']['items'][0]['quantity'],12)
            self.assertFalse(data['crafting_loot']['available'])
            bridge.clear_crafting_loot()
            self.assertNotIn('crafting_loot',bridge.data)
        finally:bridge.close()

    def test_sharing_off_by_default_and_tray_reading_is_unavailable(self):
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as folder:
            app=types.SimpleNamespace(root=root,save_quietly=MagicMock(),bridge=MagicMock(),craft_state=lambda:types.SimpleNamespace(tool=None,running=False,lite=False))
            tracker=LootTracker(app,Path(folder),{'loot_region':[1,1,200,100],'loot_enabled':True})
            try:
                self.assertFalse(tracker.share_loot.get())
                tracker.ledger.add('Elixir of Demihuman Hunt',4,kind='Crafted')
                tracker.last_scan_finished=time.time()
                with patch.object(tracker,'can_capture',return_value=(False,'BDO is in the tray')):
                    value=tracker.planner_loot_snapshot()
                self.assertFalse(value['available']);self.assertEqual(value['elixir_units'],4)
                self.assertIn('tray',value['reason'])
                tracker.share_changed();app.bridge.clear_crafting_loot.assert_called_once()
            finally:tracker.close();root.destroy()
