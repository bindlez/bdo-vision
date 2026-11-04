"""All original pages remain reachable after replacing the crowded tab strip."""
import sys,unittest,tkinter as tk
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App


class WorkspaceNavigationTests(unittest.TestCase):
    def test_groups_cover_every_page_and_reopening_preserves_selection(self):
        root=tk.Tk();root.withdraw();original=tk.Toplevel
        def hidden(*args,**kwargs):
            win=original(*args,**kwargs);win.withdraw();return win
        with patch('tkinter.Toplevel',side_effect=hidden),patch.object(App,'start_bridge'):app=App(root)
        try:
            with patch('tkinter.Toplevel',side_effect=hidden):app.loot.open()
            tabs=app.loot.tabs;nav=app.loot.navigation
            self.assertEqual(tabs.select(),str(app.loot.home.frame))
            self.assertEqual(set(tabs.tabs()),set(nav.locations))
            self.assertTrue({'Planning','History','Readers','Home','Craft','Grind','Quests'}<=set(nav.groups))
            self.assertFalse(any(isinstance(w,tk.Menubutton) for w in nav.frame.winfo_children()))
            nav.choose('Readers');self.assertEqual(len(nav.destination_buttons),6)
            self.assertEqual(nav.destination_buttons[1].cget('text'),'Loot OCR reader')
            nav.choose('History');self.assertEqual(len(nav.destination_buttons),7)
            for page,title in nav.locations.items():
                tabs.select(page);nav.sync();self.assertEqual(nav.location.get(),title)
            with patch.object(app.loot.window,'deiconify'),patch.object(app.loot.window,'lift'):app.open_activity('cp')
            nav.sync();self.assertEqual(nav.location.get(),'CP Info')
            with patch.object(app.loot.window,'deiconify'),patch.object(app.loot.window,'lift'):app.loot.open()
            self.assertEqual(tabs.select(),str(app.loot.cp_info.frame))
            target=app.loot.cp_info.target_view;before=target.plan['requiredBatches']
            self.assertFalse(target.graphs.winfo_manager());target.toggle_graphs();self.assertEqual(target.graphs.winfo_manager(),'pack')
            self.assertTrue(target.line.find_all());target.toggle_graphs();self.assertFalse(target.graphs.winfo_manager());self.assertEqual(target.plan['requiredBatches'],before)
        finally:app.loot.close();root.destroy()


if __name__=='__main__':unittest.main()
