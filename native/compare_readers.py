"""Check item/count/abstention parity after a lossless reader optimization."""
import argparse
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--before", type=Path, required=True)
p.add_argument("--after", type=Path, required=True)
p.add_argument("--frames", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
records = []
for frame in sorted(a.frames.glob("chat-*.png")):
    reports = []
    for exe in (a.before, a.after):
        result = subprocess.run([str(exe.resolve()), "--image", str(frame.resolve()), "--ensemble"],
                                capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)
        reports.append([(r["item"], r["quantity"]) for r in data["rows"]])
    records.append(dict(frame=frame.name, identical=reports[0] == reports[1], before=reports[0], after=reports[1]))
    if len(records) % 20 == 0:
        print(len(records), "frames checked", flush=True)
different = [r for r in records if not r["identical"]]
a.output.write_text(json.dumps(dict(frames=len(records), changed=len(different), records=records), indent=2), encoding="utf-8")
print(len(records), "frames;", len(different), "changed outputs")
raise SystemExit(bool(different))
