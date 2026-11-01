# 11 · Testing without risking history

## Fast feedback

Use `python dev.py test tool_reader guild_quest ocr_debug` while changing these readers. The wrapper accepts short names, full `test_` names or `.py` filenames. Unknown module names fail explicitly. Each selected module gets a temporary profile. A selected run is not a complete release qualification.

`python dev.py check` runs the complete Python suite, planner inline syntax, gear rules, untrusted-text rendering checks, compilation and handbook generation/link validation. The isolated runner writes readable logs and a machine-readable result carrying the version, source commit, test scope and failures. Inspect the summary; do not infer success merely because a report file exists.

## Layers of evidence

| Layer | What it proves | What it cannot prove |
| --- | --- | --- |
| Pure parser/state tests | Exact acceptance, rejection and lifecycle rules for supplied inputs | That OCR will produce those inputs on every game frame |
| Mocked OCR tests | Branches, timeouts, budgets, independent counter scoping | Real image recognition accuracy |
| Generated real-OCR fixtures | Tesseract integration on known text and layouts | Every BDO font/background/UI scale |
| Private annotated frame replay | Performance and extraction for those saved frames | The full live temporal pipeline |
| Native UI smoke | Widgets, initialization, state transitions and teardown | A good-looking layout at every monitor scale |
| Extracted Windows self-check | Package contents, runtime, bridge and synthetic OCR | A signed distribution or verified live grind recall |
| Live test | Behavior on one actual game/setup/session | Universal 100% accuracy or zero frame impact |

## OCR regression matrices

For tools include 0, full capacity, one/two decreases, equal neighboring values, multiple changing tools, refills, replacement, one/two missing frames, camera shifts, no anchor, ambiguous Place Mode geometry and delayed pairs. For quests include both wrapped heights, damaged separators versus damaged digits, adjacent Daily/Bonus counters, near/completion alerts and rollover after restart. For loot include repeated identical events, quantity formatting, scrolling overlap and unmatched names.

Every bug report should state the expected observation, actual result, capture availability, reader timing and whether the frame was live, generated or replayed. Save real captures privately. Public tests should use generated images or carefully minimized text fixtures without personal information.

## Visual and live checks

Open both Live OCR Reader windows and ensure images correspond to their labels, status is readable without color alone, and old images are marked as previous captures after a pause. Close and reopen during a worker to ensure stale callbacks are ignored. Check resizing and keyboard access. Then test actual game visibility, movement and quest progress; do not count a browser-covered frame as a successful game capture.

Current evidence includes automated regressions for all reader families. The saved Guild reference with a bright window behind `186/600` is still rejected rather than credited incorrectly. That limitation is explicit; neither the test count nor the documentation site changes it.

## Adding a regression

Write a small test expressing the user's behavior, not a copy of the implementation. Use deterministic clocks for elapsed-time rules and real temporary SQLite databases for persistence. Avoid brittle sleeps in unit tests. A useful rejection test proves that malformed input does not silently become a smaller valid value. Finish with the complete check when changing a shared module.
