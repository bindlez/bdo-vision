"""Non-Windows safety checks. Native tray restore must be checked in-game."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]/'desktop'))
import windows_bdo


class TrayTests(unittest.TestCase):
    def test_matches_only_black_desert_icons(self):
        for title in ('Black Desert', 'Black Desert Online (NA)', 'BlackDesert64.exe', 'BDO (Running)'):
            with self.subTest(title=title):
                self.assertTrue(windows_bdo._is_bdo_tray_label(title))
        for title in ('BDO Vision', 'Black Desert Launcher', 'Chrome',
                      'BDO Vision · Tool Watch', 'Black Desert Patcher', ''):
            with self.subTest(title=title):
                self.assertFalse(windows_bdo._is_bdo_tray_label(title))

    def test_input_never_sent_to_unverified_foreground(self):
        with patch.object(windows_bdo, 'is_verified_bdo_foreground',return_value=False):
            success,message=windows_bdo.send_ctrl_v_if_bdo_foreground()
        self.assertFalse(success)
        self.assertIn('cancelled',message.lower())

    def test_ui_automation_filters_by_exact_labels(self):
        class Fake:
            def __init__(self,text):self.text=text
            def window_text(self):return self.text
        class Container:
            def descendants(self,control_type):
                return [Fake('Google Chrome'),Fake('BDO Vision'),Fake('Black Desert Online')]
        result=windows_bdo._matching_tray_buttons(Container())
        self.assertEqual(3,len(result)) # one per control type, all BDO only
        self.assertTrue(all(item.text=='Black Desert Online' for item in result))


if __name__=='__main__':unittest.main()
