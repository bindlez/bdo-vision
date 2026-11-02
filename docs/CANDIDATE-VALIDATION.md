# Candidate validation: 1.13.0-rc.11

CP Intelligence adds 22 Python regressions, bringing the isolated suite to **350 passing tests**. Native/browser calculations agree across 100 deterministic mixed-stock, percentage, target and deployment scenarios. The actual shipped page executes in a DOM fixture covering boot, income edits, invalid inputs, reset, target allocations and graph-point selection. The native CP tab also passes a disposable-profile widget/calculation self-check. JavaScript, previous Gear/Big Drops rendering, compilation and all handbook links pass. The native example and CP data are included in extracted Windows self-checks.

All three user-supplied screenshots produced 490 total CP, 1 unused CP and 19.26% with exact two-pass agreement. A 5,664-pixel HUD crop took 0.250–0.274 seconds for both passes on this machine. A 1,000-calculation JavaScript loop took about 36–43 ms; this is arithmetic time, not total DOM render time or an FPS measurement. CP has no idle scan, recurring price refresh or animation loop. No claim of 100% accuracy across all HUD layouts or a verified new live capture is made. Windows browser control ended because its current URL could not be established reliably, so real-browser visual verification remains unclaimed; the standalone interactive preview is included for inspection.

The 750,000-catalyst example is hypothetical, not read inventory. Its NPC baseline is 15B; checked NA exchange prices can produce a much larger estimated market value. Those private market checks are not baked into a demo or shipped as fallback prices. The app reuses current cached/exact market quotes and flags missing prices and liquidation limits.

## Previous candidate · 1.13.0-rc.10

Big Drops checks cover strict Big/Huge unit-price boundaries, treasure overrides, malformed/missing values, craft exclusion, original observed timing, deduplication/restart, bounded journal versus complete totals, zero-drop baseline exposure, personal rarity samples and unchanged rare aggregates across common drops. Native smoke builds the trophy tab and displays an unpriced retained treasure. Renderer checks escape hostile data and verify ownership of the actual embedded code. Preview data is synthetic; no new real Big/Huge reveal or statistical drop-rate calibration is claimed by those checks.

## Countdown lifecycle and idle work

Integrated native-controller tests cover uncertain/missing tool matches without countdown interruption, manual pause preservation, confirmation-gate uncertainty, repeated-use and timed-pair scan holds, warning versus zero, forced manual acquisition, saved Lite settings, reuse of a verified timer, no independent quest polling, last-seen quest retention, stale-generation rejection and one shared full-image tool/quest capture. A hundred locked/Lite controller cycles perform zero foreground/capture queries or tool requests. A hundred Lite loot cycles skip region/interval setup and write the unchanged status only once. These are isolated behavior/work-count checks, not a live game performance benchmark or universal OCR acceptance.

## Completed guild widget and above-button tool reference

A private live reference contains the wrapped guild reward instruction with its heading covered, a nearby Bonus 15/100 and ordinary personal `Complete` labels. Both existing OCR passes recognize the guild completion message; the independent Bonus remains 15/100. The completion replay takes about 1.95 seconds on this machine and adds no OCR pass. The same frame's active tool is 254/3000 slightly above Place Mode. Failed ordinary discovery now recovers the Place Mode button and verifies that exact tool through bounded white-text fallback in about 2.1 seconds. These are scoped single-reference replays, not universal accuracy or live FPS measurements. Regression coverage also rejects a masked nonzero reading when the full-label empty counter is zero.

This is scoped evidence, not universal OCR acceptance or a zero-overhead claim. The complete remaining checklist is [Platform release plan](PLATFORM-RELEASE-PLAN.md).

## Tool discovery comparison

Compared the rc.3 baseline and rc.4 candidate with fresh reader instances, the same local Tesseract installation and two private saved live BDO frames. Each frame was replayed twice per reader. No game frames or private profiles are distributed.

| Metric | Baseline | Candidate |
| --- | --- | --- |
| Correct active-tool readings across four replays of two frames | 2 / 4 | 4 / 4 |
| Total OCR calls | 68 | 40 |
| Median discovery duration | 2.856 seconds | 1.961 seconds |

That comparison uses about 41% fewer OCR calls and 31% less median time while recovering the second frame. It does not measure live FPS, complete process memory, overall CPU, every camera angle or four independent scenes. Repeating the same frame is a repeatability check, not an accuracy population study. The failed baseline frame exposed a damaged separator/max-field crop; the candidate accepts a literal pair only after two complete white-glyph reads and bar-fill agreement.

An additional near-empty live reference exposed a different failure: a fragmentary dark track supplied a false percentage and vetoed a correct 353/5000 literal. The rc.6 confidence guard reads that frame correctly in approximately 2.0 seconds with 10 OCR calls. This single additional replay is separate from the comparison table and is not a universal live-accuracy claim.

## Domain calculation benchmark

Synthetic 20,000-event input, excluding input construction, OCR, Tk, network and child processes:

| Calculation | Median | Peak additional Python allocation |
| --- | --- | --- |
| Home SQLite totals | 4.776 ms | 826 bytes |
| Recipe session economics | 8.236 ms | 1,536 bytes |
| 48-point profit graph data | 5.357 ms | 320,208 bytes |

Run `python scripts/benchmark_platform.py` for a fresh local result. Allocation measurements are not the application's resident memory. The full efficiency rebuild and comparable whole-app/game-impact measurements remain separate work.

## Live evidence and remaining checks

The installed rc.3 build produced changing verified guild counters and later confirmed the active tool during crafting. Earlier attempts also became unreadable or paused while another window covered BDO. Two of those visible tool frames were used for the targeted replay above. This does not substitute for an installed rc.4 walkthrough, which must verify prompt initial selection, subsequent decreasing reads, camera motion, tool replacement, guild progress, loot, clocks and optional planner sharing together.

The compact main window was visually inspected at its real default size. Automated native checks cover primary-button visibility, wheel scrolling and advanced-control expansion/collapse. All monitor/DPI/keyboard/accessibility combinations have not been tested.

Use `python dev.py check`, then build and check the extracted Windows artifact. The release report and manifests record the actual version and committed source. Never label a package live-verified solely because these automated checks pass.
