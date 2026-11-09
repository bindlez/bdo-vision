import sys,unittest,tkinter as tk
from tkinter import ttk
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App
from activity_data import timer_earnings
from test_auto_craft import CONTEXT,ITEM,QUOTES


class AutoCraftUITests(unittest.TestCase):
    def test_no_recipe_selection_records_membership_and_updates_native_view_without_ledger_mutation(self):
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            auto=app.loot.auto_craft;db=app.loot.ledger.db
            with patch.object(auto,'context',return_value=CONTEXT),patch.object(auto,'refresh_prices'),patch.object(app.loot.insights.prices,'all',return_value=QUOTES),patch.object(app.loot,'capture_availability',return_value=(True,'')):
                app.loot.crafting.set(True);app.loot.recording.set(True)
                self.assertEqual(auto.capture_interval(5,0),1)
                self.assertEqual(auto.capture_interval(.5,0),.5)
                self.assertEqual(auto.capture_interval(5,15),5)
                app.loot.recording.set(False)
                self.assertEqual(auto.capture_interval(5,1),5)
                auto.engine.tick(CONTEXT,True,0)
                first=app.loot.ledger.add(ITEM,4,kind='Drop');auto.observe(first,ITEM,4,0);auto.engine.tick(CONTEXT,True,1)
                second=app.loot.ledger.add(ITEM,4,kind='Drop');auto.observe(second,ITEM,4,1)
                self.assertEqual(auto.snapshot(True)['recipe'],ITEM)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM auto_craft_members').fetchone()[0],2)
                self.assertTrue(all(r[6]=='Drop' for r in app.loot.ledger.rows()))
                self.assertTrue(all(r[6]=='Crafted' for r in auto.rows()))
                from platform_home import ledger_totals
                self.assertEqual(ledger_totals(db,app.loot.ledger.rows()[0][1][:10])['crafted'],8)
                self.assertEqual(timer_earnings(app.loot.insights.prices.path,QUOTES,kind='craft')['event_count'],2)
                from auto_craft_ui import CurrentCraftView
                view=CurrentCraftView(ttk.Frame(root),auto);view.refresh();self.assertIn(ITEM,view.title.get());self.assertIn('PROJECTED',view.numbers.get())
                view.toggle_graphs();self.assertTrue(view.graphs.winfo_manager());self.assertTrue(view.pies.canvas.find_all())
                auto.save();self.assertEqual(db.execute('SELECT COUNT(*) FROM auto_craft_runs').fetchone()[0],1)
                auto.enabled.set(False);auto.toggle();self.assertFalse(auto.snapshot()['available'])
            app.lite_use.set(True);self.assertIsNone(auto.context())
            with patch.object(app.loot.insights.prices,'all') as prices,patch.object(auto,'save') as save:
                for _ in range(20):auto.tick(False)
                prices.assert_not_called();save.assert_not_called()
            view.frame.destroy();auto.tick(False);auto.toggle()
        finally:app.loot.close();root.destroy()


if __name__=='__main__':unittest.main()
