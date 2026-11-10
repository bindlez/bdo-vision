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

    def test_grind_takes_dock_and_reader_without_changing_detailed_preference(self):
        app=self.app;tracker=app.loot;live=tracker.grind.live
        app.detailed_craft.set(True);tracker.crafting.set(True)
        live.open()
        self.assertIsNotNone(live.craft_metrics)
        tracker.grind.start()
        self.assertTrue(app.grind_owns_tracking());self.assertTrue(app.detailed_craft.get())
        self.assertIsNone(live.craft_metrics)
        self.assertEqual(live.hud.value_label.cget('text'),'RECORDED VALUE')
        self.assertFalse(app.detailed_tool_due(float('inf')))
        with patch.object(app,'read_ocr') as read:
            app.poll_auto_ocr();read.assert_not_called()
        app.change_detailed_craft()
        self.assertFalse(tracker.insights.session.clock.running)
        self.assertFalse(app.grind_owns_tracking())
        tracker.grind.pause()
        self.assertTrue(tracker.insights.session.clock.running)
        self.assertTrue(app.grind_owns_tracking())
        tracker.grind.finish()
        self.assertFalse(app.grind_owns_tracking())
        live.refresh()
        self.assertEqual(live.hud.value_label.cget('text'),'TOOL USES LEFT')

    def test_dock_starts_first_and_folds_tracking_without_stopping_run(self):
        self.app.loot.platform_preferences['overlay']={'locked':False}
        with patch.object(self.app.loot.grind.live,'payload',return_value={}):
            self.app.start_dock()
        live=self.app.loot.grind.live
        self.assertIsNotNone(live.hud)
        self.assertEqual(self.root.state(),'withdrawn')
        self.app.running=True
        self.app.show_timer(toggle=True)
        self.root.update_idletasks()
        self.assertEqual(self.app.dock_panels.active,'timer')
        self.assertEqual(self.root.state(),'normal')
        self.app.open_activity('grind',toggle=True)
        self.root.update_idletasks()
        self.assertEqual(self.root.state(),'withdrawn')
        self.assertEqual(self.app.loot.tabs.select(),str(self.app.loot.grind.frame))
        self.app.open_activity('craft',toggle=True)
        self.assertEqual(self.app.loot.tabs.select(),str(self.app.loot.craft_tab))
        self.app.open_activity('craft',toggle=True)
        self.assertEqual(self.app.loot.window.state(),'withdrawn')
        self.assertTrue(self.app.running)
        live.hud.dismiss()
        self.assertEqual(self.root.state(),'normal')
        self.assertIsNone(live.hud)

    def test_locked_dock_keeps_the_main_window_reachable_on_start(self):
        self.app.loot.platform_preferences['overlay']={'locked':True}
        self.app.start_dock()
        self.root.update_idletasks()
        self.assertEqual(self.root.state(),'normal')
        self.assertTrue(self.app.loot.grind.live.hud.options['locked'])
        self.app.running=True
        with patch.object(self.root,'iconify') as minimize:
            self.app.close_main_window()
            minimize.assert_called_once()
        self.assertTrue(self.app.running)

    def test_detailed_craft_metrics_are_passive_and_avoid_capture_regions(self):
        tracker=self.app.loot;live=tracker.grind.live
        self.app.detailed_craft.set(True)
        tracker.region=(1300,300,550,300)
        data={'detected':True,'current':True,'available':True,'recipe':'Elixir',
              'recordedValue':1000000,'recordedPerHour':360000000,'observedSeconds':10,
              'units':8,'items':[{'item':'Elixir','quantity':8}],'points':[(0,0),(10,1000000)]}
        area=(0,0,1920,1080)
        with patch('game_overlay.work_area',return_value=area),patch('craft_metrics_hud.work_area',return_value=area),patch.object(live,'payload',return_value={}):
            live.open();live.refresh_craft_metrics((True,''),data)
            metrics=live.craft_metrics
            self.assertTrue(metrics.shown)
            self.assertEqual(overlap(metrics.surface.rect,live.hud.surface.rect),0)
            self.assertEqual(overlap(metrics.surface.rect,tracker.region),0)
            self.assertEqual(metrics.numbers[1].cget('text'),'360.0M')
            self.assertTrue(metrics.value_graph.find_all())
            self.assertTrue(metrics.loot_graph.find_all())
            live.hud.update({'sessionActive':True})
            self.assertEqual(live.hud.rate.cget('text'),'—')
            self.app.has_reading=True;self.app.running=True;self.app.value=100
            live.hud.update({'sessionActive':True})
            self.assertEqual(live.hud.value_label.cget('text'),'TOOL USES LEFT')
            self.assertEqual(live.hud.value.cget('text'),'100')
            self.assertEqual(live.hud.rate_label.cget('text'),'TIME LEFT')
            self.assertEqual(metrics.numbers[1].cget('text'),'360.0M')
            self.app.detailed_craft.set(False);live.refresh_craft_metrics()
            self.assertIsNone(live.craft_metrics)
            live.hud.close()

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
