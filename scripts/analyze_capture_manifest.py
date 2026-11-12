"""Summarize timing and image changes in a private benchmark recording."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from PIL import Image


def analyze(folder, manifest):
    frames = manifest.get('frames', [])
    gaps = manifest.get('gaps', [])
    fps = manifest['fps']
    if not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError('Capture frame rate must be positive')
    times = [frame['at'] for frame in frames]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError('Capture timestamps must increase')
    counters = {}
    previous = {}
    for frame in frames:
        for name in ('normal', 'rare', 'chat', 'reference'):
            if name not in frame:
                continue
            with Image.open(folder / frame[name]) as image:
                pixels = image.convert('RGB')
                current = (pixels.size, hashlib.sha256(pixels.tobytes()).digest())
            entry = counters.setdefault(name, Counter())
            entry['captured'] += 1
            if name in previous:
                entry['changed' if current != previous[name] else 'unchanged'] += 1
            previous[name] = current
    intervals = [round(b - a, 4) for a, b in zip(times, times[1:])]
    return {
        'captured_pairs': len(frames),
        'rejected_samples': len(gaps),
        'reasons': dict(Counter(gap['reason'] for gap in gaps)),
        'intervals_over_two_periods': sum(interval > 2 / fps for interval in intervals),
        'largest_interval_seconds': max(intervals, default=None),
        'feeds': {name: dict(counts) for name, counts in counters.items()},
        'note': 'Image changes include background motion. OCR calls were not recorded.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        print(json.dumps(analyze(args.manifest.parent, manifest), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
