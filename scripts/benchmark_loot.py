"""Compare two ordered screenshot feeds against independently labeled drops.

Manifest: {"crafting": false, "frames": [{"chat": "chat.png",
"normal": "popup.png", "expected": [["Item name", 2]]}, ...]}.
Start with two empty frames and label new drops between each paired capture.
Paths are relative to the manifest. No game input or history writes.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from item_events import PopupSnapshots
from loot_capture import recognize_feed
from loot_tracker import TextFeedSnapshots
from price_book import PriceBook


def score(manifest, tess):
    config = json.loads(manifest.read_text(encoding='utf-8-sig'))
    book = PriceBook(':memory:')
    totals = {name: Counter() for name in ('chat', 'normal')}
    snapshots = {'chat': TextFeedSnapshots(), 'normal': PopupSnapshots(record_initial=True)}
    empty = Counter()
    for frame in config['frames']:
        expected = Counter(tuple(event) for event in frame['expected'])
        for name, tracker in snapshots.items():
            with Image.open(manifest.parent / frame[name]) as image:
                result = recognize_feed(image, tess, name, config.get('crafting', False),
                                        manifest.parent, resolve_name=book.resolve_name, diagnostics=False)
            rows = [event for event in result['events'] if book.resolve_name(event.item)]
            empty[name] = empty[name] + 1 if result['empty'] else 0
            if name == 'chat':
                fresh, _ = tracker.ingest_capture(rows, result['slots'], empty=empty[name] >= 2)
            else:
                fresh, _ = tracker.ingest(rows, empty=empty[name] >= 2)
            actual = Counter((event.item, event.quantity) for event in fresh)
            totals[name].update(correct=sum((actual & expected).values()),
                                missed=sum((expected - actual).values()),
                                extra=sum((actual - expected).values()))
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--tesseract', default='tesseract')
    args = parser.parse_args()
    for name, counts in score(args.manifest, args.tesseract).items():
        correct, missed, extra = (counts[k] for k in ('correct', 'missed', 'extra'))
        denominator = correct + missed + extra
        rate = f'{correct / denominator:.2%}' if denominator else 'no labeled events'
        print(f'{name}: {rate} exact · {correct} correct · {missed} missed · {extra} extra')


if __name__ == '__main__':
    main()
