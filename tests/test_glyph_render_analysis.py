import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from analyze_glyph_renders import analyze
from analyze_capture_manifest import analyze as analyze_capture
from benchmark_glyph_masks import classify
from score_native_events import score


class GlyphRenderAnalysisTests(unittest.TestCase):
    def test_ambiguous_templates_are_not_assigned(self):
        pixels = (1 << 100) - 1
        templates = [(('First', 1), pixels, 100), (('Second', 1), pixels, 100)]
        self.assertIsNone(classify(pixels, templates))

    def test_clear_template_recognizes_label(self):
        pixels = (1 << 100) - 1
        templates = [(('First', 1), pixels, 100), (('Second', 1), pixels << 100, 100)]
        self.assertEqual(classify(pixels, templates), ('First', 1))

    def test_background_changes_do_not_create_mask_variants(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            records = []
            for index, background in enumerate((30, 90, 30)):
                image = Image.new('RGB', (4, 3), (background,) * 3)
                image.putpixel((1, 1), (240, 240, 240))
                image.save(folder / f'{index}.png')
                records.append({'file': f'{index}.png', 'at': index * .25, 'rows': [['Item', 1]]})
            result = analyze(folder, records, (0, 0, 4, 3), 180)[0]
        self.assertEqual(result['raw_variants'], 2)
        self.assertEqual(result['mask_variants'], 1)
        self.assertEqual(result['contiguous_runs'], 1)

    def test_ambiguous_rows_break_continuity(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            image = Image.new('RGB', (2, 2), 'white')
            image.save(folder / 'frame.png')
            records = [
                {'file': 'frame.png', 'at': 0, 'rows': [['Item', 1]]},
                {'file': 'frame.png', 'at': .25, 'rows': [['Item', 1], ['Other', 1]]},
                {'file': 'frame.png', 'at': .5, 'rows': [['Item', 1]]},
            ]
            result = analyze(folder, records, (0, 0, 2, 2), 180)[0]
        self.assertEqual(result['frames'], 2)
        self.assertEqual(result['contiguous_runs'], 2)

    def test_capture_report_separates_rejections_and_changed_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            Image.new('RGB', (2, 2), 'white').save(folder / 'a.png')
            Image.new('RGB', (2, 2), 'black').save(folder / 'b.png')
            manifest = {'fps': 4, 'frames': [
                {'at': 0, 'normal': 'a.png'}, {'at': .75, 'normal': 'b.png'}],
                'gaps': [{'at': .25, 'reason': 'covered'}]}
            result = analyze_capture(folder, manifest)
        self.assertEqual(result['captured_pairs'], 2)
        self.assertEqual(result['rejected_samples'], 1)
        self.assertEqual(result['intervals_over_two_periods'], 1)
        self.assertEqual(result['feeds']['normal']['changed'], 1)

    def test_event_score_matches_repeats_once_and_reports_extra(self):
        manifest = {'frames': [{'chat': f'{i:06d}-chat.png', 'at': i * .5} for i in range(4)]}
        trace = {'frames': [
            {'file': '000000-chat.png', 'events': []},
            {'file': '000001-chat.png', 'events': [['Item', 3]]},
            {'file': '000002-chat.png', 'events': [['Item', 3]]},
            {'file': '000003-chat.png', 'events': [['Item', 3]]},
        ]}
        reference = {'scroll': [[1, [['Item', 3]]], [2, [['Item', 3]]]]}
        result = score(trace, manifest, reference)
        self.assertEqual(result['correct'], 2)
        self.assertEqual(result['extra'], 1)


if __name__ == '__main__':
    unittest.main()
