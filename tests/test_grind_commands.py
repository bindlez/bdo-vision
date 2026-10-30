import json
import sys
import tkinter as tk
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App
from planner_bridge import PlannerBridge


class GrindCommandTests(unittest.TestCase):
    def test_website_controls_apply_to_native_saved_session(self):
        root=tk.Tk();root.withdraw()
        with patch.object(App,'start_bridge'):app=App(root)
        app.bridge=bridge=PlannerBridge(Path(__file__).parents[1]/'bdo-market-intelligence.html',ports=(0,),price_book=app.loot.insights.prices)
        app.loot.share_loot.set(True);app.loot.refresh_shared_loot()
        def command(action,**fields):
            payload={'instance_id':bridge.instance_id,'action':action,**fields}
            request=urllib.request.Request(bridge.base_url+'/grind-command',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request) as response:self.assertEqual(response.status,202)
            app.tick()
        try:
            with patch.object(app.loot,'can_capture',return_value=(False,'Covered')):
                command('start',spot='Test personal route',target='Shining Powder',goal=2)
                meta=app.loot.insights.session.history()[0]
                self.assertEqual(meta['label'],'Test personal route');self.assertEqual(meta['activity'],'Grinding')
                self.assertTrue(app.loot.insights.session.clock.running)
                command('pause');self.assertFalse(app.loot.insights.session.clock.running)
                command('pause');self.assertTrue(app.loot.insights.session.clock.running)
                command('finish');self.assertTrue(app.loot.insights.session.ended)
            request=urllib.request.Request(bridge.base_url+'/show',data=json.dumps({'instance_id':bridge.instance_id}).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request) as response:self.assertEqual(response.status,200)
            self.assertTrue(bridge.consume_show_request())
        finally:app.close()
