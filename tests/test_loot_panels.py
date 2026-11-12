import sys
import unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from loot_panels import capture_panels


class PanelTests(unittest.TestCase):
    def test_covered_rare_keeps_primary(self):
        grab = Mock(return_value='pixels')
        images, errors = capture_panels({'normal': (0, 0, 100, 100), 'rare': (200, 0, 100, 100)},
            lambda regions: (regions[0][0] == 0, 'covered'), grab)
        self.assertEqual(images, {'normal': 'pixels'})
        self.assertIn('rare', errors)
        self.assertFalse(errors['rare']['empty'])
        self.assertEqual(grab.call_count, 1)

    def test_primary_covered_after_capture_rejects_pixels(self):
        visible = Mock(side_effect=[(True, ''), (False, 'covered')])
        with self.assertRaisesRegex(RuntimeError, 'covered'):
            capture_panels({'chat': (0, 0, 100, 100)}, visible, Mock())

    def test_oversized_optional_panel_is_not_captured(self):
        grab = Mock(return_value='pixels')
        images, errors = capture_panels({'normal': (0, 0, 100, 100), 'rare': (0, 0, 2000, 2000)},
                                       lambda regions: (True, ''), grab)
        self.assertEqual(grab.call_count, 1)
        self.assertIn('rare', errors)


if __name__ == '__main__': unittest.main()
