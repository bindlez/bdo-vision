import sys
import tempfile
import tkinter as tk
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from loot_ui import LootTracker
from item_events import ItemEvent


class RecordingTests(unittest.TestCase):
    def test_restart_does_not_recount_a_recent_unchanged_popup(self):
        t=self.tracker;e=ItemEvent('Elixir of Demihuman Hunt',4,'Crafted')
        t.finish(self.result([e]),t.generation)
        t.close();self.tracker=LootTracker(self.app,Path(self.temp.name),{'item_drop_region':[1200,600,300,150],'loot_enabled':True})
        self.tracker.finish(self.result([e]),self.tracker.generation)
        self.assertEqual(len(self.tracker.ledger.rows()),1)
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.temp=tempfile.TemporaryDirectory()
        self.app=types.SimpleNamespace(root=self.root,save_quietly=MagicMock())
        self.tracker=LootTracker(self.app,Path(self.temp.name),{'item_drop_region':[1200,600,300,150],'loot_enabled':True})

    def tearDown(self):
        self.tracker.close();self.root.destroy();self.temp.cleanup()

    def result(self,events):
        return {'normal':{'events':events,'empty':False,'debug':'test input','recognized':len(events)}}

    def test_first_identified_popup_is_recorded_and_repeated_frame_is_not(self):
        t=self.tracker;e=ItemEvent('Elixir of Demihuman Hunt',4,'Crafted')
        t.finish(self.result([e]),t.generation)
        self.assertEqual(t.ledger.rows()[0][2:4],(e.item,4))
        self.assertIn(e.item,t.last_read.get());self.assertIn('Saved:',t.last_saved.get())
        t.finish(self.result([e]),t.generation)
        self.assertEqual(len(t.ledger.rows()),1)
        self.assertIn('unchanged',t.last_saved.get())

    def test_preview_without_recording_and_switch_to_saved_history(self):
        t=self.tracker;t.recording.set(False)
        e=ItemEvent('Milk',3,'Drop')
        t.finish(self.result([e]),t.generation)
        self.assertEqual(t.ledger.rows(),[])
        self.assertIn('Milk',t.last_read.get())
        self.assertIn('OFF',t.last_saved.get())
        t.recording.set(True);t.toggle_recording();t.finish(self.result([e]),t.generation)
        self.assertEqual(t.ledger.rows()[0][3],3)
        self.assertTrue(t.settings()['record_loot'])

    def test_visible_guard_uses_only_configured_regions(self):
        t=self.tracker
        with patch('loot_ui.item_regions_visible',return_value=(True,'visible')) as check:
            self.assertTrue(t.can_capture()[0])
            check.assert_called_once_with([[1200,600,300,150]])

    def test_rare_failure_keeps_normal_loot(self):
        t=self.tracker
        event=ItemEvent('Black Stone',2,'Drop')
        normal={'events':[event],'empty':False,'recognized':1,'debug':'confirmed'}
        with patch('loot_ui.recognize_feed',side_effect=[normal,RuntimeError('rare timeout')]),patch.object(t.root,'after') as after:
            t.recognize({'normal':object(),'rare':object()},'tesseract',t.generation,False)
            after.call_args.args[1]()
        self.assertEqual(t.ledger.rows()[0][2:4],('Black Stone',2))
        self.assertIn('rare OCR error',t.status.get())
