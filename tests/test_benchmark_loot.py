import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from benchmark_loot import score_frames, passes_accuracy_gate, validate_labels, validate_gate_recording
from item_events import ItemEvent


class BenchmarkTests(unittest.TestCase):
    def test_gate_inclusive_boundary_and_sample_size(self):
        self.assertTrue(passes_accuracy_gate(997, 3, 0))
        self.assertFalse(passes_accuracy_gate(996, 4, 0))
        self.assertFalse(passes_accuracy_gate(299, 0, 0))
        self.assertFalse(passes_accuracy_gate(997, 3, 1))

    def test_invalid_labels_cannot_pass_as_empty(self):
        for expected in (None, '', [['Milk', True]], [['Milk', -1]], [['Milk', 1.5]], [['', 1]]):
            with self.assertRaises(ValueError):
                validate_labels({'frames': [{'expected': expected}]})
        validate_labels({'frames': [{'expected': []}]})

    def test_capture_gap_invalidates_gate(self):
        with self.assertRaises(ValueError):
            validate_gate_recording({'fps': 4, 'frames': [
                {'at': 0, 'expected': []}, {'at': 2, 'expected': []}]})

    def test_production_replay_counts_missing_extra_and_wrong_quantity(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            Image.new('RGB', (40, 40)).save(folder / 'frame.png')
            config = {'frames': [
                {'chat': 'frame.png', 'normal': 'frame.png', 'expected': []},
                {'chat': 'frame.png', 'normal': 'frame.png', 'expected': []},
                {'chat': 'frame.png', 'normal': 'frame.png', 'expected': [['Milk', 4], ['Beer', 2]]}]}
            rows = [ItemEvent('Milk', 4, 'Drop'), ItemEvent('Beer', 3, 'Drop')]
            empty = {'events': [], 'slots': [], 'empty': True}
            full = {'events': rows, 'slots': rows, 'empty': False}
            details = []
            worker = object()
            with patch('benchmark_loot.recognize_feed', side_effect=[empty, empty, empty, empty, full, full]) as reader:
                totals = score_frames(folder, config, '', lambda n: n, worker, details)
            for counts in totals.values():
                self.assertEqual(dict(counts), {'correct': 1, 'extra': 1, 'missed': 1})
            self.assertEqual(len(details), 6)
            self.assertTrue(all(call.kwargs['positioned_worker'] is worker for call in reader.call_args_list))


if __name__ == '__main__': unittest.main()
