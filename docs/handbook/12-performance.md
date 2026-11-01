# 12 · Performance engineering

## The selling point must be measured

Vision should do little when nothing changes. Low overhead depends on bounded captures, short-lived OCR workers, exact caches, work budgets, inactive-feature gating and lightweight rendering. Shorter source files alone do not imply faster execution or lower memory use. A codebase split is an organizational tool, not an optimization benchmark.

Separate idle cost, active OCR cost, transient peak memory, browser cost, disk work and game frame time. A smaller idle Python process may still start expensive OCR subprocesses. Measuring only the parent process misses their peak. A benchmark replay can compare algorithms reproducibly, but it does not measure the game's FPS.

## Existing controls to preserve

OCR subprocesses use one OpenMP thread and below-normal priority. Loot rejects oversized capture regions and shares preprocessing between passes. Tool discovery is broader only when needed; steady tracking uses crops, signatures and exact bounded numeric caches. Quest work has a short total budget, an exact-pixel result cache and no polling when disabled. Debug image previews are opt-in and reuse captures; the handbook is entirely separate from the runtime.

Tool selection has a six-second total work budget. The timed pair requires enough remaining budget before it starts and has a cooldown. Quests use a three-second deadline. Those numbers are ceilings and guards, not target latencies. Two seconds of OCR every ten seconds can still be noticeable on a weaker machine; optimize based on evidence.

## A repeatable experiment

Choose a baseline commit and candidate commit. Use the same interpreter, Tesseract, profile copy, captures and power state. Warm up imports and OCR startup separately. Replay the same labeled set, record accepted/rejected values, false positives, misses, OCR calls and elapsed time. Report median and a tail percentile, not only the fastest sample. Compare equivalent accuracy before claiming a performance gain.

`scripts/memory_probe.py --pid PID --samples 20 --interval 1` measures Windows private bytes and working set for a chosen process. It is not a whole-machine profiler. Include child OCR processes separately when analyzing active work. Use `python -m cProfile -o build/profile.pstats your_replay.py` for a controlled replay, not an indefinite real session containing private data.

## High-value optimization candidates

An anchored small-crop fast path can save discovery work if it reliably reacquires after camera movement. Backing off provisional idle tool scans could reduce work, but must still detect a newly started craft promptly. Revision-based summaries can avoid revaluing an unchanged ledger. Avoid rebuilding hidden tables and graphs. Bound retained frames and caches by entries and pixel count.

Do not remove consensus, occlusion verification or event overlap checks to win a benchmark. If an optimization changes accepted output, explain the accuracy tradeoff and validate it with annotated data. Document the environment, source identity and limits of every performance claim. The deferred full efficiency rebuild remains future work, not a claim made by this developer-tooling pass.
