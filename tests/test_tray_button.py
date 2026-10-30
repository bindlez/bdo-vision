"""Regression: Send + Tray must really schedule Ctrl+V after a successful send."""
import sys, types, unittest
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0,str(Path(__file__).parents[1]/'desktop'))
sys.modules.setdefault('winsound', types.SimpleNamespace(Beep=lambda *args: None, MessageBeep=lambda: None))
from app import App

class SendTrayTests(unittest.TestCase):
    def test_successful_send_schedules_shortcut_after_two_seconds(self):
        shell=types.SimpleNamespace(bridge=types.SimpleNamespace(server=object()),
                                    send_to_planner=lambda:True,
                                    status=MagicMock(),root=types.SimpleNamespace(after=MagicMock()),
                                    _finish_tray=lambda:None)
        App.send_and_tray(shell)
        shell.root.after.assert_called_once_with(2000,shell._finish_tray)
    def test_offline_bridge_does_not_send_keys(self):
        shell=types.SimpleNamespace(bridge=None,status=MagicMock(),root=types.SimpleNamespace(after=MagicMock()))
        App.send_and_tray(shell)
        shell.root.after.assert_not_called()
    def test_failed_send_does_not_send_keys(self):
        shell=types.SimpleNamespace(bridge=types.SimpleNamespace(server=object()),
                                    send_to_planner=lambda:False,
                                    status=MagicMock(),root=types.SimpleNamespace(after=MagicMock()))
        App.send_and_tray(shell)
        shell.root.after.assert_not_called()

if __name__=='__main__':unittest.main()
