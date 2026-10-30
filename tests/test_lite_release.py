"""Release regressions: OCR numbers, trustworthy session changes and manual sending."""
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
sys.modules.setdefault('winsound', types.SimpleNamespace(Beep=lambda *a: None, MessageBeep=lambda *a: None))
from app import App
from ocr_parser import extract_pairs
from tracking_core import ReadingGate


class LiteReleaseTests(unittest.TestCase):
    def test_parenthesized_durability(self):
        self.assertEqual(extract_pairs('Alchemy Tool (350/3000)'), [(350, 3000)])

    def test_comma_separated_durability(self):
        self.assertEqual(extract_pairs('1,350/3,000'), [(1350, 3000)])

    def test_does_not_parse_clipped_label(self):
        self.assertEqual(extract_pairs('Tool (350/)'), [])

    def test_downward_outlier_does_not_start_new_tool(self):
        gate = ReadingGate()
        self.assertEqual(gate.evaluate((180,3000), 340, 3000, 10, 1, True).kind, 'confirm')
        self.assertEqual(gate.evaluate((176,3000), 336, 3000, 15, 1, True).kind, 'accept')

    def test_send_uses_current_estimate_not_cached_ocr(self):
        now = time.monotonic()
        events = []
        class Bridge:
            server = object()
            def send(self, current, maximum, speed, **kw):
                events.append((current,maximum,speed,kw))
                return {'signal': len(events)}
        status = MagicMock()
        a = types.SimpleNamespace(
            has_reading=True,
            status=status,
            parse_inputs=lambda: (350,3000,1.,30.),
            update_value=lambda: None,
            value=345.,
            anchor=now,
            running=True,
            bridge=Bridge(),
            session_id='tool-1',
            sync_armed=False,
            pending_signal=0,
            pending_since=0,
            ack_timed_out=False,
        )
        self.assertTrue(App.send_to_planner(a))
        self.assertEqual(events[0][0],345)
        a.value=330.
        self.assertTrue(App.send_to_planner(a))
        self.assertEqual(events[1][0],330)
        self.assertEqual(events[0][3]['session_id'], events[1][3]['session_id'])

if __name__ == '__main__':
    unittest.main()
