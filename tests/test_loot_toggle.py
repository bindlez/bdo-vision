import sys
import tempfile
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from loot_ui import LootTracker


class LootToggleTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.temp=tempfile.TemporaryDirectory()
        self.app=types.SimpleNamespace(root=self.root,save_quietly=MagicMock(),craft_state=lambda:types.SimpleNamespace(tool=None,running=False,lite=False))
        self.loot=LootTracker(self.app,Path(self.temp.name),{'loot_region':[1,1,200,100]})

    def tearDown(self):
        self.loot.close();self.root.destroy();self.temp.cleanup()

    def test_capture_boxes_follow_the_selected_feed(self):
        loot=self.loot
        self.assertEqual(loot.capture_regions(),{'normal':[1,1,200,100]})
        loot.feed.set('Text feed');loot.enabled.set(True);loot.toggle()
        self.assertFalse(loot.enabled.get())
        self.assertEqual(loot.capture_regions(),{})
        loot.set_region([20,20,300,150])
        self.assertEqual(loot.capture_regions(),{'chat':[20,20,300,150]})
        loot.feed.set('Item Drop logs')
        self.assertEqual(loot.capture_regions(),{'normal':[1,1,200,100]})
        self.assertEqual(loot.settings()['text_feed_region'],[20,20,300,150])

    def test_automatic_baseline_new_events_and_ambiguous_skip(self):
        loot=self.loot;loot.enabled.set(True);loot.toggle();token=loot.generation
        loot.finish([('Stone',1)],token)
        self.assertEqual(loot.ledger.rows(),[])
        loot.finish([('Stone',1),('Relic',2)],token)
        self.assertEqual(loot.ledger.rows()[0][2:5],('Relic',2,'Text feed'))
        loot.finish([('Stone',1),('Relic',2)],token)
        loot.finish([('Unrelated',30)],token)
        self.assertEqual(len(loot.ledger.rows()),1)
        self.assertIn('uncertain skipped',loot.status.get())

    def test_toggle_off_discards_inflight_and_resume_starts_baseline(self):
        loot=self.loot;loot.enabled.set(True);loot.toggle();token=loot.generation
        loot.finish([('Stone',1)],token)
        loot.enabled.set(False);loot.toggle()
        loot.finish([('Stone',1),('Relic',2)],token)
        self.assertEqual(loot.ledger.rows(),[])
        loot.enabled.set(True);loot.toggle()
        loot.finish([('Stone',1),('Relic',2)],token)
        self.assertEqual(loot.ledger.rows(),[])
        loot.finish([('Relic',2)],loot.generation)
        self.assertEqual(loot.ledger.rows(),[])
        loot.finish([('Relic',2),('Stone',3)],loot.generation)
        self.assertEqual(loot.ledger.rows()[0][3],3)
        self.assertTrue(loot.settings()['loot_enabled'])

    def test_no_region_cannot_enable_and_no_manual_edit_actions(self):
        loot=self.loot;loot.region=None;loot.enabled.set(True);loot.toggle()
        self.assertFalse(loot.enabled.get())
        for name in ('add','correct','remove','review','scan_delayed'):
            self.assertFalse(hasattr(loot,name))

    def test_popup_crafting_and_rare_crossfeed_dedup(self):
        from item_events import ItemEvent
        loot=self.loot;loot.enabled.set(True);loot.toggle();token=loot.generation
        def result(events):return {'events':events,'empty':False,'debug':'','recognized':len(events)}
        loot.finish({'normal':result([]),'rare':result([])},token)
        # Initial empty capture establishes baseline after a second empty result.
        for name in ('normal','rare'):loot.channels[name].ingest([],empty=True)
        loot.finish({'normal':result([ItemEvent('Stone',2,'Crafted')]),'rare':result([ItemEvent('Stone',2,'Rare craft')])},token)
        rows=loot.ledger.rows()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][6],'Rare craft')
        self.assertEqual(rows[0][3],2)
        self.assertEqual(loot.safe_interval(),2)

    def test_saved_toggle_restores(self):
        self.loot.close()
        self.loot=LootTracker(self.app,Path(self.temp.name),{'loot_region':[1,1,200,100],'loot_enabled':True})
        self.assertTrue(self.loot.enabled.get())
