# Candidate validation: 1.13.0-rc.4

This is scoped evidence, not universal OCR acceptance or a zero-overhead claim. The complete remaining checklist is [Platform release plan](PLATFORM-RELEASE-PLAN.md).

## Tool discovery comparison

Compared the rc.3 baseline and rc.4 candidate with fresh reader instances, the same local Tesseract installation and two private saved live BDO frames. Each frame was replayed twice per reader. No game frames or private profiles are distributed.

| Metric | Baseline | Candidate |
| --- | --- | --- |
| Correct active-tool readings across four replays of two frames | 2 / 4 | 4 / 4 |
| Total OCR calls | 68 | 40 |
| Median discovery duration | 2.856 seconds | 1.961 seconds |

That comparison uses about 41% fewer OCR calls and 31% less median time while recovering the second frame. It does not measure live FPS, complete process memory, overall CPU, every camera angle or four independent scenes. Repeating the same frame is a repeatability check, not an accuracy population study. The failed baseline frame exposed a damaged separator/max-field crop; the candidate accepts a literal pair only after two complete white-glyph reads and bar-fill agreement.

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
