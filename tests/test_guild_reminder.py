import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from guild_reminder import explicit_absence,reminder_decision,ReminderGate


class GuildReminderTests(unittest.TestCase):
    def test_absence_requires_an_explicit_sentence(self):
        self.assertTrue(explicit_absence('There are no guild missions currently in progress.'))
        for text in ('[Daily] No active guild mission','If no active guild mission','Quest hidden','No active personal quest','The guild mission is not complete'):
            self.assertIsNone(explicit_absence(text))

    def test_missing_or_stale_is_quiet_not_authoritative_absence(self):
        for state in ({},{'available':False,'current':50,'last_at':99}, {'available':True,'current':50,'last_at':1}):
            r=reminder_decision(state,'alchemy',100,crafting=True)
            self.assertEqual(r['key'],'unverified');self.assertFalse(r['sound'])

    def test_matching_fresh_quest_suppresses_reminder(self):
        q={'available':True,'last_at':99,'current':50,'label':'[Alchemy] Guild Supply Mission'}
        self.assertIsNone(reminder_decision(q,'alchemy',100,crafting=True))
        self.assertEqual(reminder_decision(q,'cooking',100,crafting=True)['key'],'different')
        self.assertIsNone(reminder_decision(q,'alchemy',100,crafting=False))
        self.assertIsNone(reminder_decision({},'alchemy',100,enabled=False,crafting=True))

    def test_verified_absence_is_distinct_and_fresh(self):
        q={'absence_observed':True,'absence_votes':2,'absence_at':99}
        self.assertTrue(reminder_decision(q,'cooking',100,crafting=True)['sound'])
        q['absence_votes']=1
        self.assertEqual(reminder_decision(q,'cooking',100,crafting=True)['key'],'unverified')

    def test_gate_deduplicates_resets_and_snoozes(self):
        gate=ReminderGate();d={'key':'unverified'}
        self.assertEqual(gate.accept(d,'run1',100),d);self.assertIsNone(gate.accept(d,'run1',101))
        self.assertIsNone(gate.accept(None,'run1',102));self.assertEqual(gate.accept(d,'run1',103),d)
        gate.snooze(104);self.assertIsNone(gate.accept(d,'run2',105));self.assertEqual(gate.accept(d,'run2',705),d)


if __name__=='__main__':unittest.main()


class NativeReminderIntegrationTests(unittest.TestCase):
    def test_crafting_start_after_reader_and_completed_screen_produce_one_actionable_sound(self):
        import tkinter as tk
        from unittest.mock import patch
        from app import App
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            guild=app.loot.guild
            app.tool_report={'tools':[{'id':'tool','name':'Supreme Alchemy Tool'}],'active_id':'tool'}
            guild.model.accept({'completion_observed':True,'completion_votes':2,'completion_basis':'mission_message','completion_evidence':'The guild mission is complete.'},at=100)
            app.running=False
            with patch('guild_quest_ui.time.time',return_value=101),patch('guild_quest_ui.winsound.MessageBeep') as beep:
                guild.check_crafting_quest();self.assertIsNone(guild.reminder_payload)
                app.running=True;guild.check_crafting_quest()
                self.assertEqual(guild.reminder_payload['key'],'complete');self.assertIn('accept',app.status.get())
                guild.check_crafting_quest();self.assertEqual(beep.call_count,1)
            with patch('guild_quest_ui.time.time',return_value=200),patch('guild_quest_ui.winsound.MessageBeep') as beep:
                guild.check_crafting_quest();self.assertEqual(guild.reminder_payload['key'],'unverified');beep.assert_not_called()
        finally:app.loot.close();root.destroy()

    def test_completion_and_reminder_in_same_pass_do_not_double_beep(self):
        import tkinter as tk
        from unittest.mock import patch
        from app import App
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            guild=app.loot.guild
            with patch('guild_quest_ui.winsound.MessageBeep') as beep:
                guild.alert('complete');guild.play_alert_sound();self.assertEqual(beep.call_count,1)
        finally:app.loot.close();root.destroy()
