import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from overlay_layout import preferences, dock, clamp, snap, tile, overlap, RevealQueue, compact_silver
from game_overlay import passive, native_handle
from app import App


class OverlayLayoutTests(unittest.TestCase):
    def test_saved_settings_validate_untrusted_types(self):
        for raw in (None, [], 'x', {'seconds':True,'sound':'yes','position':[float('nan'),0]}):
            self.assertEqual(preferences(raw)['seconds'],7);self.assertFalse(preferences(raw)['sound'])
            self.assertNotIn('position',preferences(raw))
        self.assertEqual(preferences({'corner':'bad','density':'huge'})['corner'],'top-right')
        self.assertEqual(preferences({'position':[-1800,20],'locked':True})['position'],[-1800,20])

    def test_negative_monitor_taskbar_and_removed_monitor_are_bounded(self):
        area=(-1920,0,0,1040)
        self.assertEqual(dock((320,222),area),(-330,10,320,222))
        self.assertEqual(dock((320,222),area,'bottom-left'),(-1910,808,320,222))
        self.assertEqual(clamp((-4000,2000,320,222),area),(-1910,808,320,222))
        rect,corner=snap((-338,14,320,222),area)
        self.assertEqual((rect,corner),((-330,10,320,222),'top-right'))

    def test_tiling_avoids_hud_all_corners_and_small_work_area(self):
        for area in ((0,0,1920,1040),(-1280,-900,0,0),(0,0,800,600)):
            for corner in ('top-right','top-left','bottom-right','bottom-left'):
                hud=dock((320,222),area,corner);reveal=tile((360,204),area,hud,corner)
                self.assertEqual(overlap(hud,reveal),0,(area,corner,hud,reveal))
                self.assertEqual(clamp(reveal,area),reveal)
        self.assertEqual(clamp(tile((360,204),(0,0,300,220),(10,10,280,200)),(0,0,300,220)),(10,10,280,200))

    def test_reveal_bursts_are_bounded_deduplicated_and_expire_without_history_changes(self):
        now=[0];queue=RevealQueue(lambda:now[0])
        for i in range(8):self.assertTrue(queue.add({'id':i,'item':'Stone'}))
        self.assertEqual(len(queue.pending),4);self.assertFalse(queue.add({'id':7}))
        self.assertEqual(queue.take()['id'],4)
        now[0]=26;self.assertIsNone(queue.take());self.assertEqual(len(queue.pending),0)
        self.assertTrue(queue.add({'item':'PREVIEW'}));queue.clear();self.assertIsNone(queue.take())
        self.assertEqual(compact_silver(None),'—');self.assertEqual(compact_silver(float('inf')),'—')
        self.assertEqual(compact_silver(9_350_000_000),'9.35B')


class NativeOverlayTests(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        with patch.object(App,'start_bridge'):self.app=App(self.root)

    def tearDown(self):
        self.app.loot.close();self.root.destroy()

    def test_native_dashboard_renders_partial_prices_and_never_updates_unchanged_data(self):
        live=self.app.loot.grind.live
        data={'available':False,'sessionActive':True,'status':'capture covered','value':None,'rate':None,
              'unpriced':2,'latest':[{'item':'A drop','quantity':2}],'time':'00:02:00 / 00:00:30'}
        with patch.object(live,'payload',return_value=data):live.open()
        self.root.update_idletasks();hud=live.hud
        self.assertTrue(hud.shown);self.assertEqual(hud.surface.size,(320,268))
        self.assertIn('PAUSED',hud.status.cget('text'));self.assertIn('unpriced',hud.goal.cget('text'))
        self.assertEqual(hud.value.cget('text'),'—');self.assertEqual(hud.latest.cget('text'),'+2  A drop')
        with patch.object(hud.value,'configure') as configure:hud.update(dict(data));configure.assert_not_called()
        self.assertTrue(passive(hud.surface.window,True))
        import ctypes
        style=ctypes.windll.user32.GetWindowLongW(native_handle(hud.surface.window),-20)
        self.assertTrue(style&0x20);self.assertTrue(style&0x08000000)
        hud.close()
        with patch.object(live,'payload') as work:live.refresh();work.assert_not_called()

    def test_craft_loot_option_shows_only_current_tool_recorded_counts(self):
        live=self.app.loot.grind.live
        with patch.object(live,'payload',return_value={}):live.open()
        hud=live.hud
        self.app.has_reading=True;self.app.value=100;self.app.running=True
        self.app.loot.auto_craft.engine.run={
            'tool':self.app.session_id,'family':'fixture','counts':{'Crafted item':12,'Byproduct':2}}
        try:
            hud.update({})
            self.assertNotIn('Craft loot',hud.goal.cget('text'))
            hud.options['craft_loot']=True;hud.update({})
            self.assertIn('Crafted item × 12',hud.goal.cget('text'))
            self.assertEqual(hud.value_label.cget('text'),'TOOL USES LEFT')
            self.app.session_id='replacement'
            hud.update({})
            self.assertIn('waiting for recorded output',hud.goal.cget('text'))
        finally:
            self.app.loot.auto_craft.engine.run=None
            hud.close()

    def test_preview_is_not_loot_tiles_burst_and_cancels_callbacks(self):
        tracker=self.app.loot;big=tracker.big_drops
        before=tracker.ledger.db.execute('SELECT COUNT(*) FROM loot').fetchone()[0]
        with patch.object(tracker.grind.live,'payload',return_value={'available':False,'status':'No active run'}):tracker.grind.live.open()
        big.preview();self.root.update_idletasks()
        self.assertIsNotNone(big.toast);self.assertTrue(big.reveals.event['preview'])
        self.assertEqual(overlap(big.reveals.surface.rect,tracker.grind.live.hud.surface.rect),0)
        self.assertIsNotNone(big.reveals.job)
        big.reveal({'id':999,'category':'Treasure','item':'Test','quantity':1,'value':None})
        self.assertEqual(len(big.reveals.queue.pending),1)
        big.reveals.dismiss();self.assertEqual(big.reveals.event['id'],999)
        self.assertEqual(tracker.ledger.db.execute('SELECT COUNT(*) FROM loot').fetchone()[0],before)
        big.reveals.snooze();self.assertIsNone(big.toast);self.assertIsNone(big.reveals.job)
        big.preview();self.assertIsNone(big.toast)
        tracker.grind.live.hud.close()

    def test_failure_to_apply_passive_style_never_shows_or_leaves_pending_work(self):
        big=self.app.loot.big_drops
        with patch('game_overlay.passive',return_value=False):big.preview()
        self.assertIsNone(big.toast);self.assertIsNone(big.reveals.surface);self.assertIsNone(big.reveals.job)


if __name__=='__main__':unittest.main()
