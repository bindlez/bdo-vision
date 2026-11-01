import sys,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
import windows_bdo as win


class CaptureDiscoveryTests(unittest.TestCase):
    def setUp(self):win._capture_windows_cache=(-1e9,())

    def test_missing_game_discovery_is_shared_for_five_seconds(self):
        with patch.object(win,'is_bdo_window',return_value=False),patch.object(win,'find_bdo_windows',return_value=[]) as search:
            for now in (0,1,2,4.99):self.assertEqual(win.capture_game_windows(99,now),[])
            self.assertEqual(search.call_count,1)
            win.capture_game_windows(99,5);self.assertEqual(search.call_count,2)

    def test_foreground_game_bypasses_negative_cache_immediately(self):
        win._capture_windows_cache=(100,())
        with patch.object(win,'is_bdo_window',side_effect=lambda h:h==7),patch.object(win,'find_bdo_windows') as search:
            self.assertEqual(win.capture_game_windows(7,101),[7]);search.assert_not_called()

    def test_reused_or_closed_handle_forces_new_identity_search(self):
        win._capture_windows_cache=(100,(7,))
        with patch.object(win,'is_bdo_window',return_value=False),patch.object(win,'find_bdo_windows',return_value=[8]) as search:
            self.assertEqual(win.capture_game_windows(99,101),[8]);search.assert_called_once()

    def test_positive_cache_revalidates_game_identity_each_use(self):
        win._capture_windows_cache=(100,(7,))
        with patch.object(win,'is_bdo_window',side_effect=lambda h:h==7) as verify,patch.object(win,'find_bdo_windows') as search:
            self.assertEqual(win.capture_game_windows(99,101),[7]);verify.assert_any_call(7);search.assert_not_called()

    def test_discovery_cache_is_bounded(self):
        with patch.object(win,'is_bdo_window',return_value=False),patch.object(win,'find_bdo_windows',return_value=list(range(100))):
            self.assertEqual(len(win.capture_game_windows(999,0)),8)

    def test_coverage_is_never_cached_when_another_window_covers_game(self):
        user=MagicMock();user.GetForegroundWindow.return_value=7
        user.IsWindowVisible.return_value=True;user.IsIconic.return_value=False
        user.GetAncestor.return_value=7
        with patch.object(win,'_user32',return_value=user),patch.object(win,'capture_game_windows',return_value=[7]),patch.object(win,'_contains_region',return_value=True),patch.object(win,'_process_name',return_value='other.exe'):
            self.assertTrue(win.item_regions_visible([[0,0,30,30]])[0])
            user.GetAncestor.return_value=9
            self.assertFalse(win.item_regions_visible([[0,0,30,30]])[0])
