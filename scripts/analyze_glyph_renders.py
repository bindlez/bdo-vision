"""Compare labeled, fixed-position text crops in a private recording.

Input is a JSON list of {file, rows, at} records. Each row is [name, quantity].
Only frames with one recognized row are used, so a label cannot be assigned to
the wrong physical row. Labels may come from OCR and are not ground truth.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from PIL import Image


def analyze(folder, records, box, threshold):
    groups = defaultdict(lambda: {'raw': Counter(), 'mask': Counter(), 'occurrences': 0})
    previous = None
    previous_time = None
    for record in records:
        rows = record.get('rows', [])
        if len(rows) != 1:
            previous = None
            previous_time = None
            continue
        name, quantity = rows[0]
        if not isinstance(name, str) or not isinstance(quantity, int):
            raise ValueError('Each label must have an item name and integer quantity')
        path = folder / record['file']
        with Image.open(path) as source:
            if not (0 <= box[0] < box[2] <= source.width and 0 <= box[1] < box[3] <= source.height):
                raise ValueError(f'Crop exceeds image bounds: {path.name}')
            image = source.convert('RGB').crop(box)
        raw = hashlib.sha256(image.tobytes()).hexdigest()
        pixels = image.load()
        mask = bytes(
            1 if min(pixels[x, y]) > threshold and max(pixels[x, y]) - min(pixels[x, y]) < 25 else 0
            for y in range(image.height)
            for x in range(image.width)
        )
        mask_hash = hashlib.sha256(mask).hexdigest()
        key = (name, quantity)
        group = groups[key]
        group['raw'][raw] += 1
        group['mask'][mask_hash] += 1
        stamp = record.get('at')
        if key != previous or stamp is None or previous_time is None or not 0 < stamp - previous_time <= .4:
            group['occurrences'] += 1
        previous, previous_time = key, stamp

    output = []
    for (name, quantity), group in groups.items():
        total = sum(group['raw'].values())
        output.append({
            'item': name,
            'quantity': quantity,
            'frames': total,
            'contiguous_runs': group['occurrences'],
            'raw_variants': len(group['raw']),
            'mask_variants': len(group['mask']),
            'most_common_mask_frames': group['mask'].most_common(1)[0][1],
        })
    return sorted(output, key=lambda row: row['frames'], reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('labels', type=Path)
    parser.add_argument('--box', required=True, help='Left,top,right,bottom in each crop')
    parser.add_argument('--threshold', type=int, default=180)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        box = tuple(int(value) for value in args.box.split(','))
        if len(box) != 4 or not 0 <= args.threshold <= 255:
            raise ValueError('Invalid crop or threshold')
        records = json.loads(args.labels.read_text(encoding='utf-8-sig'))
        report = {'box': box, 'threshold': args.threshold,
                  'label_source': str(args.labels), 'groups': analyze(args.labels.parent, records, box, args.threshold)}
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    result = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(result, encoding='utf-8')
    else:
        print(result)


if __name__ == '__main__':
    main()
