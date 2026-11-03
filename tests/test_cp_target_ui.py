from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App


class CPTargetUITests(unittest.TestCase):
    def test_native_target_changes_quantities_and_invalid_input_hides_previous_plan(self):
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            view=app.loot.cp_info;view.build(ttk.Notebook(root));root.update_idletasks()
            goal=view.target_view;original=goal.plan['requiredBatches']
            self.assertEqual(len(goal.tree.get_children()),6)
            view.fields['target'].set('525');self.assertTrue(view.recalculate(save=False))
            self.assertGreater(goal.plan['requiredBatches'],original);self.assertEqual(goal.plan['target'],525)
            goal.tree.selection_set('leaf');goal.choose();self.assertIn('Blush Leaf',goal.details.get())
            view.fields['target'].set('invalid');self.assertFalse(view.recalculate(save=False));self.assertIsNone(goal.plan)
            self.assertFalse(goal.tree.get_children())
            view.fields['target'].set('500');self.assertTrue(view.recalculate(save=False));self.assertEqual(goal.plan['target'],500)
            quotes={'Clear Liquid Reagent':{'unit_price':12000},'Milk':{'unit_price':10000},'Stonetail Fodder':{'unit_price':4000000}}
            with patch.object(app.loot.insights.prices,'all',return_value=quotes):
                view.fields['income'].set('1000000');view.recalculate(save=False)
                view.chart_mode.set('Allocation frontier');view.draw_chart();self.assertEqual(len(view.frontier_points),21)
                x,y,split=view.frontier_points[10]
                view.choose_frontier(type('Event',(),{'x':x,'y':y})());self.assertEqual(view.report['split'],split)
                view.chart_mode.set('Income sensitivity');view.draw_chart();self.assertFalse(view.frontier_points)
                view.update_recovery(10);self.assertIn('SIMULATION',view.recovery.get())
                view.selected.set('Target, then cash');view.recalculate(save=False);view.solve_income()
                self.assertGreater(float(view.fields['income'].get()),0)
                view.apply_best();self.assertEqual(int(view.fields['target'].get()),view.analysis['optimized']['cp'])
                self.assertIn('Mysterious Catalyst',view.text_views['Exchanges'].get('1.0','end'))
                from test_workerman import JOB,QUOTES
                worker=view.workerman
                with patch.object(worker.provider(),'cached',return_value=None):worker.toggle()
                worker.accept({'revision':'a'*40,'jobs':[JOB]})
                with patch.object(app.loot.insights.prices,'all',return_value=QUOTES):
                    view.fields['target'].set('492');view.recalculate(save=False)
                    self.assertIn('Break-even:',worker.status.get());self.assertIsNotNone(worker.model['breakEvenDays'])
                    worker.fields['additionalCp'].set('3');worker.use_target();self.assertEqual(view.report['target'],493)
                    worker.fields['moveSpeed'].set('0');worker.update();self.assertIsNone(worker.model);self.assertIn('Check worker',worker.status.get())
                    worker.fields['moveSpeed'].set('7.5');view.recalculate(save=False)
                    self.assertEqual(view.settings()['cp_plan']['workerman']['node'],'131')
                    worker.toggle();self.assertFalse(worker.frame.winfo_manager())
        finally:
            app.loot.close();root.destroy()


if __name__=='__main__':unittest.main()
