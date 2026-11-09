import sys
import tkinter as tk
import unittest
from pathlib import Path

from PIL import Image, ImageTk

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from heavy_tools import ScreenshotLab, icon_key, slot_boxes


class ScreenshotLabTests(unittest.TestCase):
    def test_grid_covers_every_source_pixel_once(self):
        self.assertEqual(slot_boxes((5, 4, 22, 21), 2, 2), [
            (5, 4, 13, 12), (13, 4, 22, 12), (5, 12, 13, 21), (13, 12, 22, 21),
        ])
        with self.assertRaises(ValueError):
            slot_boxes((0, 0, 1000, 1000), 16, 16)

    def test_review_shows_match_unknown_and_ambiguous(self):
        root = tk.Tk()
        root.withdraw()
        try:
            lab = ScreenshotLab(root)
            lab.image = Image.new('RGB', (90, 30), 'red')
            lab.image.paste('green', (30, 0, 60, 30))
            lab.image.paste('blue', (60, 0, 90, 30))
            lab.photo = ImageTk.PhotoImage(lab.image)
            lab.selection = (0, 0, 90, 30)
            lab.columns.set('3')
            lab.references = {
                icon_key(lab.image.crop((0, 0, 30, 30))): {'Helmet'},
                icon_key(lab.image.crop((60, 0, 90, 30))): {'Boots A', 'Boots B'},
            }
            lab.review()
            self.assertEqual(lab.results.get(0, 'end'), (
                '01  Helmet', '02  Unknown', '03  Ambiguous · Boots A, Boots B',
            ))
            self.assertIsNotNone(lab.slot_photo)
        finally:
            root.destroy()
