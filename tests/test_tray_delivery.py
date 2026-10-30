"""Verify the exact Ctrl+V key sequence; live tray transitions remain Windows-only."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'desktop'))
import windows_bdo

class _Callable:
    def __init__(self,callback): self.callback=callback
    def __call__(self,*args): return self.callback(*args)

class _User32:
    def __init__(self,count=4):
        self.count=count
        self.sent=[]
        self.SendInput=_Callable(self._send)
    def __post_init__(self):
        pass
    def _send(self,n,seq,size):
        self.sent.append([(int(seq[i].u.ki.wVk),int(seq[i].u.ki.dwFlags)) for i in range(n)])
        return self.count if n==4 else 2

class TrayDeliveryTests(unittest.TestCase):
    def test_sends_ctrl_v_in_correct_order_and_releases(self):
        fake=_User32()
        with patch.object(windows_bdo,'is_verified_bdo_foreground',return_value=True),patch.object(windows_bdo,'_user32',return_value=fake):
            ok,msg=windows_bdo.send_ctrl_v_if_bdo_foreground()
        self.assertTrue(ok,msg)
        self.assertEqual(fake.sent[0],[(0x11,0),(0x56,0),(0x56,2),(0x11,2)])
    def test_partial_delivery_attempts_key_release(self):
        fake=_User32(count=2)
        with patch.object(windows_bdo,'is_verified_bdo_foreground',return_value=True),patch.object(windows_bdo,'_user32',return_value=fake):
            ok,msg=windows_bdo.send_ctrl_v_if_bdo_foreground()
        self.assertFalse(ok)
        self.assertEqual(fake.sent[1],[(0x56,2),(0x11,2)])

if __name__=='__main__': unittest.main()
