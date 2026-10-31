import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App, DEFAULT


class AutoOCRTests(unittest.TestCase):
    def app(self):
        return types.SimpleNamespace(auto_enabled=types.SimpleNamespace(get=lambda:True),region_confirmed=True,selecting_region=False,
            bdo_foreground=lambda:True,busy=False,loot=types.SimpleNamespace(busy=False),
            safe_scan_interval=lambda:10,last_scan_started=0,auto_health=MagicMock(),root=MagicMock(),read_ocr=MagicMock(),poll_auto_ocr=MagicMock())

    def test_due_scan_and_heartbeat(self):
        app=self.app();App.poll_auto_ocr(app)
        app.read_ocr.assert_called_once_with(delayed=False,automatic=True)
        self.assertGreater(app.last_scan_started,0)
        app.root.after.assert_called_once()

    def test_foreground_and_setup_gates(self):
        app=self.app();app.bdo_foreground=lambda:False
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()
        self.assertIn('BDO',app.auto_health.set.call_args.args[0])
        app=self.app();app.region_confirmed=False
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()

    def test_worker_failure_does_not_stop_polling(self):
        app=self.app();app.read_ocr.side_effect=RuntimeError('failure')
        App.poll_auto_ocr(app)
        app.root.after.assert_called_once()
        self.assertIn('retry',app.auto_health.set.call_args.args[0])

    def test_default_and_interval_not_due(self):
        self.assertEqual(DEFAULT['scan_interval'],10)
        self.assertTrue(DEFAULT['auto_scan'])
        app=self.app()
        import time
        app.last_scan_started=time.monotonic()
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()

    def test_grinding_does_not_launch_unrelated_tool_ocr(self):
        app=self.app();app.running=False
        app.loot.enabled=types.SimpleNamespace(get=lambda:True)
        app.loot.crafting=types.SimpleNamespace(get=lambda:False)
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()
        self.assertIn('grinding',app.auto_health.set.call_args.args[0])
        app.loot.crafting.get=lambda:True
        App.poll_auto_ocr(app);app.read_ocr.assert_called_once()
