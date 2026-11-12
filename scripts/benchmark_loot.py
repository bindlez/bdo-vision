"""Compare two ordered screenshot feeds against independently labeled drops.

Manifest: {"crafting": false, "frames": [{"chat": "chat.png",
"normal": "popup.png", "expected": [["Item name", 2]]}, ...]}.
Start with two empty frames and label new drops between each paired capture.
Paths are relative to the manifest. No game input or history writes.
"""
import argparse
from collections import Counter, defaultdict, deque
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from item_events import PopupSnapshots
from loot_capture import recognize_feed
from loot_tracker import TextFeedSnapshots
from price_book import PriceBook


def score(manifest, tess, *, catalog=None, windows_ocr=None):
    config = json.loads(manifest.read_text(encoding='utf-8-sig'))
    if not config['frames'] or any(frame.get('expected') is None for frame in config['frames']):
        raise ValueError('Label every frame with expected new drops before scoring.')
    book = PriceBook(':memory:')
    if catalog:
        from item_catalog import DiskItemDatabase
        book._item_database = DiskItemDatabase(catalog)
    with ExitStack() as resources:
        worker = None
        if windows_ocr:
            from windows_ocr import WindowsOCR
            worker = WindowsOCR(windows_ocr)
            resources.callback(worker.close)
        return score_frames(manifest.parent, config, tess, book.resolve_name, worker)


def validate_gate_recording(config):
    fps = config.get('fps')
    stamps = [frame.get('at') for frame in config.get('frames', [])]
    if not isinstance(fps, (int, float)) or not 1 <= fps <= 8 or len(stamps) < 2:
        raise ValueError('Accuracy gate needs a timestamped capture with a declared frame rate.')
    if any(type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < 0 for stamp in stamps):
        raise ValueError('Accuracy gate needs valid capture timestamps.')
    if config.get('gaps') or any(not 0 < b-a <= 2/fps for a, b in zip(stamps, stamps[1:])):
        raise ValueError('Accuracy gate needs uninterrupted capture at the declared cadence.')


def passes_accuracy_gate(correct, missed, extra):
    return correct + missed >= 300 and 1000 * correct > 997 * (correct + missed + extra)


def score_frames(folder, config, tess, resolve_name, worker):
    totals = {name: Counter() for name in ('chat', 'normal')}
    snapshots = {'chat': TextFeedSnapshots(), 'normal': PopupSnapshots(record_initial=True)}
    pending = {name: defaultdict(deque) for name in snapshots}
    empty = Counter()
    for index, frame in enumerate(config['frames']):
        stamp = frame.get('at', index)
        lag = 2 if 'at' in frame else 0
        expected = [tuple(event) for event in frame['expected']]
        for name, tracker in snapshots.items():
            with Image.open(folder / frame[name]) as image:
                if name == 'normal' and worker is not None:
                    from popup_hybrid import recognize_popup
                    result = recognize_popup(image, tess, worker, resolve_name, config.get('crafting', False))
                else:
                    result = recognize_feed(image, tess, name, config.get('crafting', False),
                                            folder, resolve_name=resolve_name, diagnostics=False)
            rows = [event for event in result['events'] if resolve_name(event.item)]
            empty[name] = empty[name] + 1 if result['empty'] else 0
            if name == 'chat':
                fresh, _ = tracker.ingest_capture(rows, result['slots'], empty=empty[name] >= 2)
            else:
                fresh, _ = tracker.ingest(rows, empty=empty[name] >= 2)
            for key, times in list(pending[name].items()):
                while times and stamp - times[0] > lag:
                    times.popleft()
                    totals[name]['missed'] += 1
                if not times:
                    del pending[name][key]
            for event in expected:
                pending[name][event].append(stamp)
            for event in fresh:
                key = (event.item, event.quantity)
                times = pending[name].get(key)
                if times:
                    times.popleft()
                    totals[name]['correct'] += 1
                else:
                    totals[name]['extra'] += 1
    for name, queue in pending.items():
        totals[name]['missed'] += sum(map(len, queue.values()))
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--tesseract', default='tesseract')
    parser.add_argument('--catalog', type=Path, help='Use the installed catalog read-only')
    parser.add_argument('--windows-ocr', type=Path, help='Replay the hybrid popup candidate with this OCR helper')
    parser.add_argument('--gate', action='store_true', help='Require more than 99.7%% accuracy on 300 or more labeled drops')
    args = parser.parse_args()
    if args.gate:
        try:
            validate_gate_recording(json.loads(args.manifest.read_text(encoding='utf-8-sig')))
        except ValueError as exc:
            parser.error(str(exc))
    passed = False
    for name, counts in score(args.manifest, args.tesseract, catalog=args.catalog, windows_ocr=args.windows_ocr).items():
        correct, missed, extra = (counts[k] for k in ('correct', 'missed', 'extra'))
        denominator = correct + missed + extra
        rate = f'{correct / denominator:.2%}' if denominator else 'no labeled events'
        print(f'{name}: {rate} exact · {correct} correct · {missed} missed · {extra} extra')
        passed |= passes_accuracy_gate(correct, missed, extra)
    if args.gate and not passed:
        raise SystemExit('Accuracy gate failed. Need 300 labeled drops and one feed above 99.7%.')


if __name__ == '__main__':
    main()
