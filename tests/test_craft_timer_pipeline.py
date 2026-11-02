"""Real controller lifecycle without game capture or a real user profile."""
from pathlib import Path
from unittest.mock import Mock,patch
import sys,tkinter as tk,unittest
from types import SimpleNamespace
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import app as app_module
from app import App
from tool_reader import AutomaticToolReader


class CraftTimerPipelineTests(unittest.TestCase):
    def test_paired_quest_waits_for_busy_loot_then_expires_without_sticking(self):
        guild=self.app.loot.guild;guild.enabled.set(True);self.app.loot.busy=True;callbacks=[]
        with patch.object(self.root,'after',side_effect=lambda delay,fn:callbacks.append(fn) or 'queued'):
            guild.scan(paired=True)
            self.assertTrue(guild.waiting);self.assertEqual(guild.phase,'queued');self.assertEqual(len(callbacks),1)
            self.clock=104;callbacks[0]()
            self.assertFalse(guild.waiting);self.assertEqual(guild.phase,'retry');self.assertIsNone(guild.pending)

    def test_smart_quest_watch_is_opt_in_and_lite_cancels_it(self):
        guild=self.app.loot.guild;guild.enabled.set(True);guild.schedule();self.assertIsNone(guild.watch_pending)
        guild.watch.set(True);guild.schedule();self.assertIsNotNone(guild.watch_pending)
        self.app.lite_use.set(True);self.app.change_lite_use();self.assertIsNone(guild.watch_pending)
        with patch.object(guild,'scan') as scan:guild.poll();scan.assert_not_called()

    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.clock=100.
        self.clock_patch=patch('app.time.monotonic',side_effect=lambda:self.clock);self.clock_patch.start()
        with patch.dict(app_module.config,{'lite_use':False,'auto_scan':True,'auto_tool_discovery':True,'loot_enabled':False,'guild_quest_enabled':False,'seconds_per_craft':1}),patch.object(App,'start_bridge'):
            self.app=App(self.root)
        self.app.alarm=Mock()

    def tearDown(self):
        self.app.loot.close();self.root.destroy();self.clock_patch.stop()

    def feed(self,current=100,wear=0,confirmation='Place Mode position',active=True,unreadable=False):
        row={'id':'tool-1','name':'Alchemy Tool','current':current,'maximum':3000,'state':'Verified','wear_streak':wear,'votes':2}
        report={'tools':[row] if active else [],'active_id':'tool-1' if active else None,'active_key':'tool-1:0' if active else None,
                'confirmation':confirmation,'unreadable':[{'name':'Alchemy Tool'}] if unreadable else [],'duration':.2,'ocr_calls':2,
                'captured_at':1000+self.clock,'captured_mono':self.clock}
        self.app.finish_tools(report,self.app.tool_reader,True,1000+self.clock,self.clock)

    def test_unclear_or_missing_tool_does_not_stop_or_rearm_existing_countdown(self):
        self.feed();session=self.app.session_id;alarm=self.app.alarmed
        for second,unclear in ((102,True),(104,False)):
            self.clock=second;self.feed(active=False,unreadable=unclear)
            self.assertTrue(self.app.running);self.assertEqual(self.app.value,200-second)
            self.assertEqual(self.app.session_id,session);self.assertEqual(self.app.alarmed,alarm)
        self.app.tick();self.assertIn('ESTIMATE',self.app.timer_state.get())
        self.assertIn('assumes crafting continues',self.app.source.get())

    def test_miss_never_starts_a_timer_or_resumes_manual_pause(self):
        self.feed(active=False,unreadable=True);self.assertFalse(self.app.running)
        self.feed();self.app.pause();value=self.app.value
        self.clock=110;self.feed(active=False,unreadable=True)
        self.assertFalse(self.app.running);self.assertEqual(self.app.value,value)

    def test_confirmed_use_stops_all_automatic_tool_work_until_zero_not_warning(self):
        self.feed();self.assertFalse(self.app._tool_scan_latched)
        self.clock=102;self.feed(98,2,'Repeated durability decreases')
        self.assertTrue(self.app._tool_scan_latched);self.assertEqual(self.app.tool_status.stage,'timer')
        with patch.object(self.app,'bdo_foreground',return_value=True) as foreground,patch.object(self.app,'read_ocr') as scan:
            for _ in range(100):self.app.poll_auto_ocr()
            foreground.assert_not_called();scan.assert_not_called()
            self.clock=191;self.app.tick();self.app.poll_auto_ocr()
            self.app.alarm.assert_called_once();self.assertTrue(self.app._tool_scan_latched);scan.assert_not_called()
            self.clock=200;self.app.tick();self.assertFalse(self.app._tool_scan_latched)
            self.app.poll_auto_ocr();scan.assert_called_once_with(delayed=False,automatic=True)

    def test_one_lite_read_starts_countdown_then_all_ocr_stays_off_after_expiry(self):
        self.app.lite_use.set(True);self.app.change_lite_use();self.feed()
        self.assertTrue(self.app.lite_scan_complete);self.assertFalse(self.app._tool_scan_latched)
        self.assertEqual(self.app.tool_status.stage,'timer')
        with patch.object(self.app,'bdo_foreground') as foreground,patch.object(self.app,'read_ocr') as scan:
            for _ in range(100):self.app.poll_auto_ocr()
            self.clock=210;self.app.tick();self.app.poll_auto_ocr()
            self.assertEqual(self.app.value,0);self.app.alarm.assert_called_once()
            foreground.assert_not_called();scan.assert_not_called()
        self.assertTrue(self.app.lite_scan_complete)

    def test_two_frame_use_confirmation_also_stops_tool_ocr(self):
        self.feed(100,0,'two-frame comparison')
        self.assertTrue(self.app._tool_scan_latched)

    def test_reading_gate_uncertainty_does_not_lock_or_stop_the_countdown(self):
        self.feed();self.clock=101
        self.feed(500,2,'Repeated durability decreases')
        self.assertIsNotNone(self.app.reading_gate.pending)
        self.assertFalse(self.app._tool_scan_latched);self.assertTrue(self.app.running)

    def test_lite_reuses_running_verified_timer_and_cancels_quest_poll(self):
        self.feed();self.clock=103;self.app.update_value();value=self.app.value;session=self.app.session_id
        self.app.loot.guild.enabled.set(True);self.app.loot.guild.schedule(1000)
        self.assertIsNone(self.app.loot.guild.pending)
        self.app.lite_use.set(True);self.app.change_lite_use()
        self.assertTrue(self.app.lite_scan_complete);self.assertIsNone(self.app.loot.guild.pending)
        self.assertEqual((self.app.value,self.app.session_id),(value,session))
        self.app.loot.guild.schedule();self.assertIsNone(self.app.loot.guild.pending)
        self.app.lite_use.set(False);self.app.change_lite_use();self.assertIsNone(self.app.loot.guild.pending)

    def test_guild_read_is_paired_with_tool_attempt_including_lite_and_failure(self):
        guild=self.app.loot.guild;guild.enabled.set(True);self.app.lite_use.set(True)
        with patch.object(self.app,'finish_tools') as finish,patch.object(self.app,'tool_failed') as failed,patch.object(guild,'scan') as scan:
            self.app.finish_tool_attempt({},self.app.tool_reader,True,1000,100,guild_generation=guild.generation)
            finish.assert_called_once();scan.assert_called_once_with(paired=True,sample=None)
            scan.reset_mock()
            self.app.finish_tool_attempt(None,self.app.tool_reader,True,None,None,guild_generation=guild.generation,error='unclear')
            failed.assert_called_once();scan.assert_called_once_with(paired=True,sample=None)
            scan.reset_mock()
            self.app.finish_tool_attempt({},AutomaticToolReader(),True,1000,100,guild_generation=guild.generation)
            self.app.finish_tool_attempt({},self.app.tool_reader,True,1000,100,guild_generation=guild.generation-1)
            scan.assert_not_called()

    def test_quest_has_no_independent_scan_and_preserves_last_seen_in_lite(self):
        guild=self.app.loot.guild;guild.enabled.set(True)
        guild.model.accept({'current':184,'target':600},at=100)
        self.app.lite_use.set(True)
        with patch('guild_quest_ui.ImageGrab.grab') as capture:
            guild.scan();guild.poll();guild.schedule()
            capture.assert_not_called()
        guild.refresh();self.assertEqual(guild.progress.get(),'184 / 600')
        self.assertIn('LAST SEEN',guild.state.get());self.assertIsNone(guild.pending)

    def test_lite_tool_and_guild_share_one_capture_and_start_timer_before_quest_finishes(self):
        guild=self.app.loot.guild;guild.enabled.set(True);self.app.lite_use.set(True)
        pending=[];box=(800,100,995,600);scene=Image.new('RGB',(1000,700),'black')
        def tool_read(tess,bounds,grab,**kwargs):
            self.assertFalse(kwargs['confirm_pair']);grab((0,0,1000,700))
            return {'tools':[{'id':'tool-1','name':'Alchemy Tool','current':100,'maximum':3000,'state':'Verified','votes':2}],
                    'active_id':'tool-1','active_key':'tool-1:0','confirmation':'Place Mode position','duration':.2,'ocr_calls':2}
        with patch('app.foreground_bdo_capture_bounds',return_value=(1,0,0,1000,700)),patch.object(guild,'capture_region',return_value=box),\
             patch('app.ImageGrab.grab',return_value=scene) as capture,patch.object(self.app.tool_reader,'read',side_effect=tool_read),\
             patch('guild_quest_ui.recognize_quest',return_value=({'current':49,'target':600},'agreed')) as quest,\
             patch('app.threading.Thread',side_effect=lambda target,**kw:SimpleNamespace(start=target)),\
             patch.object(self.root,'after',side_effect=lambda delay,fn:pending.append(fn)):
            self.app.capture_tools(self.app.tess.get(),automatic=True)
            self.assertEqual(len(pending),1);pending.pop(0)()
            self.assertTrue(self.app.running);self.assertTrue(self.app.lite_scan_complete)
            self.assertTrue(guild.busy);self.assertEqual(len(pending),1)
            pending.pop(0)();self.assertFalse(guild.busy)
            self.assertEqual(guild.model.current,49);self.assertEqual(len(pending),0)
            capture.assert_called_once();quest.assert_called_once()

    def test_manual_scan_rearms_one_lite_acquisition_and_automatic_entry_is_guarded(self):
        self.app.lite_use.set(True);self.app.change_lite_use();self.feed()
        self.app._tool_scan_latched=True
        with patch.object(self.app,'capture_tools') as capture:
            self.app.read_ocr(delayed=False,automatic=True);capture.assert_not_called();self.assertFalse(self.app.busy)
            self.app.read_ocr(delayed=False,automatic=False)
        self.assertFalse(self.app.lite_scan_complete);self.assertFalse(self.app._tool_scan_latched);self.assertTrue(self.app.busy)

    def test_saved_lite_mode_cannot_be_disabled_by_stale_auto_scan_preferences(self):
        other=tk.Toplevel(self.root)
        try:
            with patch.dict(app_module.config,{'lite_use':True,'auto_scan':False,'auto_tool_discovery':False}),patch.object(App,'start_bridge'):
                second=App(other)
            self.assertTrue(second.auto_enabled.get());self.assertTrue(second.auto_tools.get())
            self.assertFalse(second.lite_scan_complete)
            second.loot.close()
        finally:other.destroy()

    def test_lite_loot_poll_skips_capture_setup_and_repeated_status_updates(self):
        self.app.lite_use.set(True);loot=self.app.loot
        with patch.object(loot,'can_capture') as visible,patch.object(loot,'safe_interval') as interval,patch.object(loot.capture_state,'set',wraps=loot.capture_state.set) as state:
            for _ in range(100):loot.poll()
            visible.assert_not_called();interval.assert_not_called();state.assert_called_once()
