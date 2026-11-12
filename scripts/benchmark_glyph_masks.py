"""Evaluate fixed-crop text masks on a separate labeled recording.

Training and evaluation labels are JSON lists with `file` and `rows` entries.
This measures visible row labels, not unique loot events or session accuracy.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import time

from PIL import Image


def mask(path, box, threshold):
    with Image.open(path) as source:
        if not (0 <= box[0] < box[2] <= source.width and 0 <= box[1] < box[3] <= source.height):
            raise ValueError(f'Crop exceeds image bounds: {path}')
        image = source.convert('RGB').crop(box)
    values = bytearray()
    pixels = image.tobytes()
    for index in range(0, len(pixels), 3):
        red, green, blue = pixels[index:index + 3]
        values.append(int(min(red, green, blue) > threshold and max(red, green, blue) - min(red, green, blue) < 25))
    return int.from_bytes(values, 'little')


def train(path, box, threshold):
    records = json.loads(path.read_text(encoding='utf-8-sig'))
    templates = []
    for record in records:
        rows = record.get('rows', [])
        if len(rows) != 1:
            raise ValueError('Training images need exactly one label')
        value = mask(path.parent / record['file'], box, threshold)
        if not value:
            raise ValueError(f'Empty template: {record["file"]}')
        templates.append((tuple(rows[0]), value, value.bit_count()))
    if not templates:
        raise ValueError('At least one template is required')
    return templates


def classify(value, templates, minimum=.72, margin=.009):
    size = value.bit_count()
    if size < 80:
        return None
    scores = {}
    for label, template, template_size in templates:
        score = 2 * (value & template).bit_count() / (size + template_size)
        scores[label] = max(scores.get(label, 0), score)
    ranked = sorted(scores.items(), key=lambda entry: entry[1], reverse=True)
    if ranked[0][1] < minimum or len(ranked) > 1 and ranked[0][1] - ranked[1][1] < margin:
        return None
    return ranked[0][0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('training', type=Path)
    parser.add_argument('evaluation', type=Path)
    parser.add_argument('--box', default='62,316,350,336')
    parser.add_argument('--threshold', type=int, default=180)
    parser.add_argument('--minimum-score', type=float, default=.72)
    parser.add_argument('--details', type=Path, help='Save per-frame comparisons locally')
    args = parser.parse_args()
    try:
        box = tuple(int(value) for value in args.box.split(','))
        if len(box) != 4 or not 0 <= args.threshold <= 255 or not 0 <= args.minimum_score <= 1:
            raise ValueError('Invalid crop, threshold, or minimum score')
        if args.training.resolve().parent == args.evaluation.resolve().parent:
            raise ValueError('Training and evaluation must use separate recordings')
        templates = train(args.training, box, args.threshold)
        records = json.loads(args.evaluation.read_text(encoding='utf-8-sig'))
        counts = Counter()
        details = []
        start = time.perf_counter()
        for record in records:
            rows = record.get('rows', [])
            if len(rows) != 1:
                continue
            actual = classify(mask(args.evaluation.parent / record['file'], box, args.threshold), templates,
                              minimum=args.minimum_score)
            expected = tuple(rows[0])
            counts['frames'] += 1
            counts['abstained' if actual is None else 'matches' if actual == expected else 'disagrees'] += 1
            if args.details:
                details.append({'file': record['file'], 'expected': expected, 'actual': actual})
        report = {'counts': dict(counts), 'minimum_score': args.minimum_score,
                  'wall_seconds': round(time.perf_counter() - start, 3),
                  'scope': 'Row observations, not unique loot or accuracy proof'}
        if args.details:
            args.details.write_text(json.dumps(details, indent=2), encoding='utf-8')
        print(json.dumps(report, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
