# Native reader lab 01 — 2026-10-30

This is a development checkpoint, not a production tracker release. The released Python app and protected history are untouched. The branch also contains the previously committed, unpublished rc.3 extraction audit. The VERSION file refers to that candidate, not a published native release.

## Implementation

The prototype uses C++20, direct Win32/GDI screen capture and widgets, Windows image decoding, local glyph templates, an embedded public name catalog, conservative model votes, and bounded caches. /MT statically links the C++ runtime. The executable imports USER32, GDI32, ole32, COMDLG32, SHELL32 and KERNEL32. Windows image codecs are instantiated through COM. It does not invoke Python, Tesseract or a separate model service.

The experimental UI supports saved-image reading and an explicitly selected system-text region. Foreground/process and region-point checks suspend covered/background capture. These checks are not exhaustive occlusion detection. There is no production ledger, market/bridge or tray integration. The temporal overlap core is ported and tested but is not yet connected to persistent recording. Recognition caching never decides whether loot is new.

## Measurements

One sequential replay, same Windows machine, 83 saved frames, 658 detected row slots:

| Reader change | Median frame | p95 frame | Total process CPU | Peak private | Peak working set |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial ensemble | 316.817 ms | 376.887 ms | 17,765.625 ms | 2,048,000 B | 13,942,784 B |
| Bounded catalog-result cache | 272.607 ms | 318.999 ms | 15,468.750 ms | 2,072,576 B | 13,869,056 B |
| Reuse observed columns and advance-prefix sums | 13.476 ms | 20.368 ms | 1,343.750 ms | 2,109,440 B | 13,922,304 B |

Each pass accepted 635 row observations and had 56 exact row-mask cache hits. These are repeated visible observations, **not unique loot events or accuracy labels**. Whole-process CPU includes image decoding and startup; reader frame timings exclude image decoding. A separate before/after replay compared every row's item, quantity and abstention on all 83 frames: zero changed outputs. The final transformation eliminates repeated computations without changing the scoring formula or thresholds.

Development labels: 63/64 rows matched, zero extra/wrong accepted rows. Separate recording labels: 23/24 matched, zero extra/wrong accepted rows. Two of the holdout frames contain the same retained row contents over different backgrounds, so the 24 rows are not 24 independent loot events. The holdout miss is a blue implicit-one Laila's Petal; the development miss is Black Stone. Fonts/models and confusion weights were selected using the development set. These small, correlated samples do not support a 100% accuracy claim or session-level missed-loot rate.

Unchanged-frame repeated reads were around 1.35 ms. The final saved-image GUI smoke read all eight rows correctly in a labeled image, with 2,691,072 B private and 18,141,184 B working set. This was a hidden GUI smoke run with native controls created; it excludes interactive file-dialog overhead and is not a live-game or complete-app memory benchmark. File-dialog shell extensions, real display state and added bridge/history features can change memory use.

The lab executable is 4,568,064 bytes, including the embedded names. SHA256: `e068f1e0581bf791fe0ac60b1e9b0dc07e2e87bf8106bdc452e240e0a7d5d04a`.

## Validation and next gates

4,039 native assertions pass: bounded/malformed quantities, negative blank/noise backgrounds, baseline/retained/blocked feeds, pending-hole recovery, ambiguous no-overlap abstention, and 2,000 scrolling events exactly once. This is an assertion count, not thousands of independent OCR test images. The project runner also passes all 141 existing regressions in separate disposable profiles. A bulk single-process run is unsuitable for the Tk modules; the isolated project runner is the authoritative result.

Before replacing the existing app:

1. Expand independently labeled recordings across real scales, fonts, quantities, rarity colors, wrapped rows, clutter and other-player notifications. Fix implicit-one misses without inflating counts or guessing rare drops.
2. Validate foreground, partial occlusion, minimize/restore and selection cancellation in a live game. Recalibrate safely when the game font changes without resizing the selected rectangle.
3. Connect temporal overlap to a disposable native ledger, including original observation times for recovered holes and conservative gaps. Preserve the protected profile and compatible single-writer lock before migration.
4. Port exact market identity resolution, regional price snapshots, optional website sharing, crafting/grind clocks and tray restoration. Keep estimates out of recorded loot.
5. Measure the complete foreground/background runner, including idle CPU, private memory, working set, capture work, ledger writes and bridge requests. Compare the same workload with other trackers before any “#1 leanest” claim.

Private evidence is retained under the workspace's `qa-20/`: `native-sequence-83.json`, `native-sequence-catalog-cache.json`, `native-sequence-shared-columns.json`, `native-lossless-parity.json`, `native-optimized-gold.json`, `native-session-holdout.json`, `native-gui-smoke.json`, and `native-isolated-regressions.txt`. Captures and ledgers are never published.
