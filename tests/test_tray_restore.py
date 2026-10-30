"""Safe tray restore logic: only BDO-labeled icons get clicked."""
import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'desktop'))
import windows_bdo

class FakeIcon:
 def __init__(self,label):self.label=label;self.calls=0
 def window_text(self):return self.label
 def click_input(self):self.calls+=1
 def double_click_input(self):self.calls+=1

class FakeContainer:
 def descendants(self,control_type):
  return [FakeIcon('Google Chrome'), FakeIcon('BDO Vision'),FakeIcon('Black Desert Online')]

class RestoreTests(unittest.TestCase):
 def test_tray_identity_accepts_black_spirit(self):
  self.assertTrue(windows_bdo._is_bdo_tray_label('Black Spirit'))
  self.assertFalse(windows_bdo._is_bdo_tray_label('BDO Vision'))
 def test_find_icons_finds_only_bdo(self):
  class Desktop:
   def window(self,**kwargs):return FakeContainer()
   def windows(self):return []
  icons=windows_bdo._find_tray_icons(Desktop())
  self.assertTrue(icons)
  self.assertTrue(all('Black Desert' in x.window_text() for x in icons))
 def test_restore_never_runs_when_foreground_already_visible(self):
  with patch.object(windows_bdo,'_bdo_window_visible',return_value=True),patch.object(windows_bdo,'restore_bdo',return_value=(True,'Restored')) as restore:
   self.assertEqual(windows_bdo.super_restore_bdo(),(True,'Restored'))
   restore.assert_called_once()

if __name__=='__main__':unittest.main()
