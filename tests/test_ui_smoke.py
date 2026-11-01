"""Construct the real Windows widgets without capturing the game or opening ports."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tkinter as tk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from app import App


class DesktopSmokeTests(unittest.TestCase):
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
            app.bridge=None;root.deiconify();app.open_tools();root.update()
            app.tool_status.accept({'tools':[{'id':'tool-1','name':'Alchemy Tool','current':95,'maximum':3000,'state':'Visible'}]})
            app.refresh_tool_view();root.update_idletasks()
            self.assertTrue(app.tool_tree.exists('tool-1'))
            app.tool_tree.selection_set('tool-1');app.refresh_tool_view()
            self.assertEqual(app.tool_tree.selection(),('tool-1',))
            self.assertIn('95/3,000',app.tool_preview.get())
            app.loot.ledger.add('Milk',3);app.loot.silver.refresh()
            tree=app.loot.silver.tree
            self.assertTrue(tree.exists('Milk'))
            tree.selection_set('Milk')
            with patch.object(tree,'move',wraps=tree.move) as move:
                app.loot.silver.refresh();move.assert_not_called()
            self.assertEqual(tree.selection(),('Milk',))
            app.loot.ledger.add('Milk',2);app.loot.silver.refresh()
            self.assertEqual(tree.item('Milk')['values'][2],5)
            app.open_guild_quest();root.update_idletasks()
            self.assertEqual(app.loot.tabs.select(),str(app.loot.guild.frame))
            self.assertFalse(app.loot.guild.enabled.get());self.assertIsNone(app.loot.guild.pending)
            app.loot.guild.model.accept({'current':184,'target':600},at=100)
            app.loot.guild.refresh();self.assertEqual(app.loot.guild.progress.get(),'184 / 600')
            with patch('guild_quest_ui.winsound.MessageBeep') as beep:
                app.loot.guild.alert('test');beep.assert_called_once()
            self.assertEqual(app.loot.guild.model.current,184)
        finally:
            if "app" in locals():app.loot.close()
            root.destroy()
