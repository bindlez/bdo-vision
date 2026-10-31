"""Developer-only replay runner. Labels/captures remain outside the repository.

Use a different recording session for holdout labels; this runner does not make
development labels independent simply by replaying them.
"""
import argparse
import collections
import json
import statistics
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = []
    hits = extras = misses = 0
    for filename, expected in json.loads(args.labels.read_text(encoding="utf-8")).items():
        result = subprocess.run(
            [str(args.exe.resolve()), "--image", str(args.frames / filename),
             "--ensemble", "--repeat", "20"],
            capture_output=True, text=True, check=True, timeout=30,
        )
        report = json.loads(result.stdout)
        actual = collections.Counter((r["item"], r["quantity"]) for r in report["rows"] if r["item"])
        truth = collections.Counter(map(tuple, expected))
        hit, extra, miss = (sum((truth & actual).values()),
                            sum((actual - truth).values()), sum((truth - actual).values()))
        hits += hit
        extras += extra
        misses += miss
        records.append(dict(frame=filename, matched=hit, extra=extra, missed=miss, report=report))
        print(filename, hit, extra, miss, flush=True)
    summary = dict(matched=hits, extra=extras, missed=misses,
                   cold_median_ms=statistics.median(r["report"]["cold_ms"] for r in records),
                   unchanged_median_ms=statistics.median(r["report"]["warm_ms"] for r in records),
                   peak_private_bytes=max(r["report"]["private_bytes"] for r in records),
                   peak_working_set_bytes=max(r["report"]["working_set_bytes"] for r in records))
    args.output.write_text(json.dumps(dict(summary=summary, records=records), indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
