"""Compare experimental native event traces with a timestamped reference."""
import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path


def score(trace, manifest, reference, lag=2.0):
    times = {frame['chat']: frame['at'] for frame in manifest['frames']}
    labels = dict(reference['scroll'])
    pending = defaultdict(deque)
    totals = Counter()
    previous = -1
    for frame in trace['frames']:
        name = frame['file']
        stamp = times[name]
        index = int(name.split('-', 1)[0])
        if stamp <= previous:
            raise ValueError('Trace is not in capture order')
        previous = stamp
        for queue in pending.values():
            while queue and stamp - queue[0] > lag:
                queue.popleft()
                totals['missed'] += 1
        for event in labels.get(index, []):
            pending[tuple(event)].append(stamp)
        for event in frame['events']:
            queue = pending[tuple(event)]
            if queue:
                queue.popleft()
                totals['correct'] += 1
            else:
                totals['extra'] += 1
        totals['ambiguous_frames'] += bool(frame.get('ambiguous'))
        totals['gaps'] += bool(frame.get('gap_before'))
    totals['missed'] += sum(map(len, pending.values()))
    return dict(totals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('reference', type=Path)
    args = parser.parse_args()
    try:
        data = [json.loads(path.read_text(encoding='utf-8-sig'))
                for path in (args.trace, args.manifest, args.reference)]
        print(json.dumps(score(*data), indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
