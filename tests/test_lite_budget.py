"""Timer-only mode must not repeatedly query prices, capture or write sessions."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from insights_ui import LootInsights


class LiteBudgetTests(unittest.TestCase):
    def test_transition_publishes_pause_once_then_ticks_stay_idle(self):
        tracker=Mock()
        tracker.app.lite_use.get.return_value=True
        tracker.home=None
        view=SimpleNamespace(closed=False,last_lite_mode=None,tracker=tracker,session=Mock(),prices=Mock(),root=Mock(),state=Mock())
        view.tick=lambda:LootInsights.tick(view)
        for _ in range(100):view.tick()
        tracker.capture_clock.tick.assert_called_once_with(False,'Lite Use · timer only')
        tracker.refresh_shared_loot.assert_called_once_with()
        view.session.tick.assert_called_once_with(False)
        tracker.capture_availability.assert_not_called()
        view.prices.refresh_async.assert_not_called()
        self.assertEqual(view.root.after.call_count,100)
        view.state.set.assert_not_called()
