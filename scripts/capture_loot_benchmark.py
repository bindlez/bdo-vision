"""Collect paired, private BDO loot crops without waiting for OCR."""
import argparse
import io
import json
from pathlib import Path
import sys
import time

from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from loot_capture import capture_budget
from windows_bdo import item_regions_visible


def region(value):
    try:
        rect = tuple(int(part) for part in value.split(','))
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use x,y,width,height') from exc
    if len(rect) != 4:
        raise argparse.ArgumentTypeError('Use x,y,width,height')
    return rect


def collect(folder, boxes, seconds, fps):
    folder.mkdir(parents=True, exist_ok=False)
    left = min(box[0] for box in boxes.values())
    top = min(box[1] for box in boxes.values())
    right = max(box[0] + box[2] for box in boxes.values())
    bottom = max(box[1] + box[3] for box in boxes.values())
    regions = list(boxes.values())
    start = time.monotonic()
    stored_bytes = 0
    frames, gaps = [], []
    try:
        for index in range(seconds * fps):
            due = start + index / fps
            time.sleep(max(0, due - time.monotonic()))
            stamp = round(time.monotonic() - start, 4)
            ready, reason = item_regions_visible(regions)
            if not ready:
                gaps.append({'at': stamp, 'reason': reason})
                continue
            image = ImageGrab.grab((left, top, right, bottom), all_screens=True)
            ready, reason = item_regions_visible(regions)
            if not ready:
                gaps.append({'at': stamp, 'reason': reason})
                continue
            data = {}
            for name, (x, y, width, height) in boxes.items():
                stream = io.BytesIO()
                image.crop((x-left, y-top, x-left+width, y-top+height)).save(stream, format='PNG', compress_level=1)
                data[name] = stream.getvalue()
            stored_bytes += sum(map(len, data.values()))
            if stored_bytes > 512 * 1024 * 1024:
                gaps.append({'at': stamp, 'reason': 'Storage limit reached'})
                break
            frame = {'at': stamp, 'expected': None}
            for name, pixels in data.items():
                filename = f'{index:06d}-{name}.png'
                (folder / filename).write_bytes(pixels)
                frame[name] = filename
            frames.append(frame)
    finally:
        report = {'frames': frames, 'gaps': gaps, 'fps': fps}
        (folder / 'manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return len(frames), len(gaps)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--chat', type=region, required=True)
    parser.add_argument('--normal', type=region, required=True)
    parser.add_argument('--reference', type=region, help='Optional independent evidence crop, such as tool durability')
    parser.add_argument('--seconds', type=int, default=120)
    parser.add_argument('--fps', type=int, default=4)
    args = parser.parse_args()
    boxes = {'chat': args.chat, 'normal': args.normal}
    if args.reference:
        boxes['reference'] = args.reference
    ready, reason = capture_budget(list(boxes.values()))
    if not ready:
        parser.error(reason)
    if not (1 <= args.seconds <= 300 and 1 <= args.fps <= 8):
        parser.error('Use 1–300 seconds and 1–8 frames per second')
    frames, gaps = collect(args.folder, boxes, args.seconds, args.fps)
    print(f'{frames} paired frames, {gaps} blocked samples. Label expected events in manifest.json before scoring.')


if __name__ == '__main__':
    main()
