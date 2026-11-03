import json,sys,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from grind_charts import personal_best
from planner_bridge import PlannerBridge
from app import App


class GrindPresentationTests(unittest.TestCase):
    def test_personal_best_reprices_history_and_requires_comparable_time_spot_and_items(self):
        row={'id':'live','spot':'Forest','observed_seconds':600,'value':1200,'silver_hour':7200,'unpriced':0}
        peer={'id':'old','spot':'forest','ended_at':1,'observed_seconds':600,'items':[{'item':'Stone','quantity':10,'value':1}]}
        prices={'Stone':{'unit_price':100}}
        race=personal_best(row,[peer],prices)
        self.assertEqual(race['bestHour'],6000);self.assertEqual(race['pacePercent'],120);self.assertEqual(race['aheadSilver'],200)
        for change in ({'spot':'Other'},{'ended_at':None},{'observed_seconds':59},{'activity':'Hunting'}):self.assertIsNone(personal_best(row,[{**peer,**change}],prices))
        self.assertIsNone(personal_best({**row,'unpriced':1},[peer],prices));self.assertIsNone(personal_best(row,[peer],{}))

    def test_stream_is_explicitly_opt_in_and_same_origin(self):
        bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,))
        try:
            with urllib.request.urlopen(bridge.base_url+'/stream') as response:self.assertIn(b'textContent',response.read())
            with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(bridge.base_url+'/stream-state')
            self.assertEqual(exc.exception.code,403)
            bridge.stream_enabled=True;bridge.stream_snapshot={'available':False,'status':'Paused','value':100,'updatedAt':1}
            with urllib.request.urlopen(bridge.base_url+'/stream-state') as response:self.assertEqual(json.load(response)['value'],100)
            request=urllib.request.Request(bridge.base_url+'/stream-state',headers={'Origin':'https://evil.example'})
            with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(request)
            self.assertEqual(exc.exception.code,403)
        finally:bridge.close()

    def test_native_charts_clear_and_overlay_work_is_opt_in(self):
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        try:
            g=app.loot.grind;g.build(ttk.Notebook(root))
            self.assertFalse(g.obs_enabled.get())
            with patch.object(g.live,'payload') as work:g.live.refresh();work.assert_not_called()
            row={'items':[{'item':'Stone','value':100}], 'observed_seconds':60,'excluded_seconds':60,'coverage':.5,'unpriced':1}
            g.charts.draw(row);self.assertTrue(g.charts.canvas.find_all());g.charts.draw(None);self.assertFalse(g.charts.canvas.find_all())
            self.assertFalse(g.live.payload()['available'])
            g.silver_goal.set('1000');g.start();g.silver_goal.set('2000');g.apply_silver_goal()
            self.assertEqual(g.summaries()[0]['silver_goal'],2000)
            self.assertEqual(g.live.payload()['silverGoal'],2000)
            ident=app.loot.ledger.add('Stone',2);g.insights.session.observe(ident,True);g.insights.session.clock.seconds=60
            with patch.object(g.insights.prices,'all',return_value={'Stone':{'unit_price':50,'source':'Test'}}):
                first=g.live.payload();self.assertEqual(first['value'],100);self.assertEqual(first['rate'],6000)
                with patch('live_grind.time.time',return_value=first['updatedAt']+2):self.assertEqual(g.live.payload()['value'],100)
            g.silver_goal.set('-1');g.apply_silver_goal();self.assertEqual(g.summaries()[0]['silver_goal'],2000)
            g.finish();self.assertEqual(g.summaries()[0]['silver_goal'],2000)
            with patch.object(g,'summaries',wraps=g.summaries) as summary:g.refresh();self.assertEqual(summary.call_count,1,'one visible refresh must reuse one history calculation')
        finally:app.loot.close();root.destroy()


if __name__=='__main__':unittest.main()
