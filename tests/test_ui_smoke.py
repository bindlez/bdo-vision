"""Construct the real Windows widgets without capturing the game or opening ports."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from app import App


class DesktopSmokeTests(unittest.TestCase):
    def test_enabled_capture_does_not_open_workspace_on_startup(self):
        import app as app_module
        from loot_ui import LootTracker
        root=tk.Tk();root.withdraw();app=None
        try:
            with patch.dict(app_module.config,{'loot_enabled':True,'item_drop_region':[0,0,100,100],'auto_scan':False,'guild_quest_enabled':False}),patch.object(App,'start_bridge'),patch.object(LootTracker,'poll'):
                app=App(root)
                root.after(750,root.quit);root.mainloop()
                self.assertTrue(app.loot.enabled.get())
                self.assertIsNone(app.loot.window)
        finally:
            if app:
                with patch.object(app.loot,'capture_availability',return_value=(False,'Test profile')):app.close()
            else:root.destroy()

    def test_startup_settings_and_send_states(self):
        root = tk.Tk()
        root.withdraw()
        try:
            with patch.object(App, 'start_bridge'):
                app = App(root)
            root.update_idletasks()
            self.assertEqual(str(app.send_button['state']), 'disabled')
            app.has_reading = True
            app.bridge = type('Bridge', (), {'server': True})()
            app.refresh_action_states()
            self.assertEqual(str(app.send_button['state']), 'normal')
            app.bridge=None
            app.open_settings()
            root.update_idletasks()
            self.assertTrue(app.settings_window.winfo_exists())
            app.loot.open()
            root.update_idletasks()
            self.assertTrue(app.loot.window.winfo_exists())
            self.assertEqual(len(app.loot.tree.get_children()),len(app.loot.ledger.rows()))
            app.open_activity('home');root.update_idletasks()
            self.assertEqual(app.loot.tabs.select(),str(app.loot.home.frame))
            app.loot.home.goal.set('500');app.loot.home.save_goal()
            self.assertEqual(app.loot.platform_preferences['daily_goal'],500)
            app.loot.ledger.add('Test craft',100,kind='Crafted');app.loot.refresh()
            self.assertIn('100 recorded units',app.loot.craft_dashboard.summary.get())
            self.assertEqual(app.loot.craft_dashboard.data[-1],100)
            app.open_activity('craft');self.assertEqual(app.loot.tabs.select(),str(app.loot.craft_tab))
            root.update()
            craft_canvas=next(w for w in app.loot.craft_tab.winfo_children() if isinstance(w,tk.Canvas))
            before=craft_canvas.yview()
            app.loot.craft_dashboard.frame.winfo_children()[0].event_generate('<MouseWheel>',delta=-120)
            root.update_idletasks()
            self.assertGreater(craft_canvas.yview()[0],before[0])
            app.bridge=None;root.deiconify();root.update()
            self.assertLessEqual(root.winfo_width(),400)
            self.assertLessEqual(root.winfo_height(),600)
            for button in (app.scan_button,app.send_button,app.tray_button):
                self.assertTrue(button.winfo_ismapped())
                self.assertLessEqual(button.winfo_rootx()+button.winfo_width(),root.winfo_rootx()+root.winfo_width())
                self.assertLessEqual(button.winfo_rooty()+button.winfo_height(),root.winfo_rooty()+root.winfo_height())
            def descendants(widget):
                for child in widget.winfo_children():yield child;yield from descendants(child)
            more=next(w for w in descendants(root) if isinstance(w,tk.Button) and w.cget('text')=='MORE CONTROLS ▾')
            more.invoke();root.update();self.assertTrue(app.auto_toggle.winfo_ismapped())
            more.invoke();root.update();self.assertFalse(app.auto_toggle.winfo_ismapped())
            app.open_tools();root.update()
            app.tool_status.accept({'tools':[{'id':'tool-1','name':'Alchemy Tool','current':95,'maximum':3000,'state':'Visible'}]})
            app.refresh_tool_view();root.update_idletasks()
            self.assertTrue(app.tool_tree.exists('tool-1'))
            app.tool_debug.open();root.update_idletasks()
            self.assertTrue(app.tool_debug.opened);app.tool_debug.close()
            app.tool_tree.selection_set('tool-1');app.refresh_tool_view()
            self.assertEqual(app.tool_tree.selection(),('tool-1',))
            self.assertIn('95/3,000',app.tool_preview.get())
            self.assertIn('estimate',app.tool_tree['columns'])
            self.assertEqual(app.tool_tree.item('tool-1')['values'][2],'≈ 95')
            app.loot.ledger.add('Milk',3);app.loot.silver.refresh()
            tree=app.loot.silver.tree
            self.assertTrue(tree.exists('Milk'))
            tree.selection_set('Milk')
            with patch.object(tree,'move',wraps=tree.move) as move:
                app.loot.silver.refresh();move.assert_not_called()
            self.assertEqual(tree.selection(),('Milk',))
            app.loot.ledger.add('Milk',2);app.loot.silver.refresh()
            self.assertEqual(tree.item('Milk')['values'][2],5)
            app.loot.tabs.select(app.loot.silver.frame);root.update()
            page=app.loot.silver.frame
            page.page_canvas.yview_moveto(1);root.update_idletasks()
            footer=page.page_content.winfo_children()[-1]
            self.assertLessEqual(footer.winfo_rooty()+footer.winfo_height(),page.page_canvas.winfo_rooty()+page.page_canvas.winfo_height()+2)
            app.open_guild_quest();root.update_idletasks()
            self.assertEqual(app.loot.tabs.select(),str(app.loot.guild.frame))
            app.loot.guild.reader_view.open();root.update_idletasks()
            self.assertTrue(app.loot.guild.reader_view.opened);app.loot.guild.reader_view.close()
            self.assertFalse(app.loot.guild.enabled.get());self.assertIsNone(app.loot.guild.pending)
            app.loot.guild.model.accept({'current':184,'target':600},at=100)
            app.loot.guild.refresh();self.assertEqual(app.loot.guild.progress.get(),'184 / 600')
            with patch('guild_quest_ui.winsound.MessageBeep') as beep:
                app.loot.guild.alert('test');beep.assert_called_once()
            self.assertEqual(app.loot.guild.model.current,184)
            app.loot.guild.finish({'current':184,'target':600,'objectives':[{'key':'daily:oil','kind':'Daily','objective':'Make Oil','current':31,'target':100},{'key':'bonus:reagent','kind':'Bonus','objective':'Make Reagent','current':21,'target':100}]},'',app.loot.guild.generation,100,.1,False)
            self.assertEqual(len(app.loot.guild.objective_tree.get_children()),2)
            self.assertEqual(app.loot.ledger.db.execute('SELECT count(*) FROM quest_objectives').fetchone()[0],2)
            with patch.object(app.loot.guild,'schedule'),patch('guild_quest_ui.winsound.MessageBeep') as beep:
                app.loot.guild.finish({'completion_observed':True,'completion_votes':2,'completion_basis':'reward_message','completion_evidence':'Claim your rewards via the Complete Mission button in the Guild Mission window.'},'',app.loot.guild.generation,110,.1,False)
                self.assertEqual(app.loot.guild.progress.get(),'Complete')
                self.assertIn('Guild quest: Complete',app.loot.guild.state.get())
                self.assertIn('Last numeric counter: 184 / 600',app.loot.guild.detail.get())
                self.assertEqual(app.loot.guild.read_failures,0);beep.assert_called_once()
                app.loot.guild.refresh();beep.assert_called_once()
            app.busy=True;app.loot.guild.enabled.set(True)
            with patch.object(app.loot.guild,'schedule'):
                app.loot.guild.scan(paired=True);self.assertFalse(app.loot.guild.waiting)
            app.busy=False;app.loot.guild.enabled.set(False);app.loot.guild.toggle();self.assertFalse(app.loot.guild.waiting)
        finally:
            if "app" in locals():app.loot.close()
            root.destroy()
