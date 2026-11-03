from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App
from craft_economy import craft_spec


class ImperialUITests(unittest.TestCase):
    def test_native_rankings_stock_cards_filter_shared_cp_and_advanced_details(self):
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            tabs=ttk.Notebook(root);app.loot.cp_info.build(tabs);view=app.loot.imperial;view.build(tabs)
            quotes={m['name']:{'item_id':m['id'],'unit_price':100,'stock':1000000000,'region':'NA'} for m in craft_spec()['items'].values()}
            with patch.object(app.loot.insights.prices,'all',return_value=quotes):
                view.cp.set('491');self.assertTrue(view.recalculate(save=False));self.assertEqual(view.boxes,245)
                self.assertTrue(all(view.winners));self.assertEqual(app.loot.cp_info.fields['cp'].get(),'491')
                view.guru.set(True);view.recalculate(save=False);self.assertTrue(all(b['boxId']==9856 for b,_ in view.rows.values()))
                view.toggle_advanced();self.assertTrue(view.advanced.winfo_manager());self.assertIn('STOCKED CRAFT',view.detail.get())
                view.kind.set('Alchemy');view.change_kind();self.assertTrue(all(b['boxId']==9871 for b,_ in view.rows.values()))
                view.mastery.set('invalid');self.assertFalse(view.recalculate(save=False));self.assertFalse(view.rows)
        finally:
            app.loot.close();root.destroy()


if __name__=='__main__':unittest.main()
