import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from app import App, DEFAULT


class AutoOCRTests(unittest.TestCase):
    def test_manual_tool_read_waits_for_game_without_taking_a_capture(self):
        app=types.SimpleNamespace(bdo_foreground=lambda:False,capture_tools=MagicMock(),set_tool_stage=MagicMock(),root=MagicMock(),wait_for_tool_capture=MagicMock(),busy=True,scan_button=None)
        App.wait_for_tool_capture(app,'engine',float('inf'))
        app.capture_tools.assert_not_called();app.root.after.assert_called_once()
        app.bdo_foreground=lambda:True;App.wait_for_tool_capture(app,'engine',float('inf'))
        app.capture_tools.assert_called_once_with('engine',False)
        app.bdo_foreground=lambda:False;app.capture_tools.reset_mock();App.wait_for_tool_capture(app,'engine',-1)
        self.assertFalse(app.busy);app.capture_tools.assert_not_called()
    def app(self):
        return types.SimpleNamespace(lite_use=types.SimpleNamespace(get=lambda:False),lite_scan_complete=False,auto_enabled=types.SimpleNamespace(get=lambda:True),region_confirmed=True,selecting_region=False,
            bdo_foreground=lambda:True,busy=False,loot=types.SimpleNamespace(busy=False),
            safe_scan_interval=lambda:10,last_scan_started=0,auto_health=MagicMock(),root=MagicMock(),read_ocr=MagicMock(),poll_auto_ocr=MagicMock())

    def test_due_scan_and_heartbeat(self):
        app=self.app();App.poll_auto_ocr(app)
        app.read_ocr.assert_called_once_with(delayed=False,automatic=True)
        self.assertGreater(app.last_scan_started,0)
        app.root.after.assert_called_once()

    def test_lite_mode_scans_until_accepted_then_stops(self):
        app=self.app();app.lite_use=types.SimpleNamespace(get=lambda:True)
        App.poll_auto_ocr(app);app.read_ocr.assert_called_once()
        app.read_ocr.reset_mock();app.lite_scan_complete=True
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()
        self.assertIn('LITE USE',app.auto_health.set.call_args.args[0])

    def test_automatic_tool_finder_needs_no_initial_region(self):
        app=self.app();app.region_confirmed=False
        app.auto_tools=types.SimpleNamespace(get=lambda:True)
        app.tool_reader=types.SimpleNamespace(next_due=0)
        App.poll_auto_ocr(app);app.read_ocr.assert_called_once_with(delayed=False,automatic=True)

    def test_foreground_and_setup_gates(self):
        app=self.app();app.bdo_foreground=lambda:False
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()
        self.assertIn('BDO',app.auto_health.set.call_args.args[0])
        app=self.app();app.region_confirmed=False
        App.poll_auto_ocr(app);app.read_ocr.assert_not_called()

    def test_return_to_game_rechecks_immediately(self):
        app=self.app();app.auto_tools=types.SimpleNamespace(get=lambda:True)
        app.tool_reader=types.SimpleNamespace(next_due=float('inf'))
        app.tool_status=types.SimpleNamespace(stage='paused');app.set_tool_stage=MagicMock()
        App.poll_auto_ocr(app)
        self.assertEqual(app.tool_reader.next_due,0)
        app.read_ocr.assert_called_once_with(delayed=False,automatic=True)

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
