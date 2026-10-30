# 1.9.0-rc.1 · measured efficiency work

## Release scope

This candidate reduces the cost of the existing Windows tracker and packages a friend-test application. The browser demo is separate, uses simulated drops and fixed example prices, and has no live screen access. Full-session OCR recall against a competing tracker remains unverified. A 100% live accuracy claim is not made.

## Results on the development PC

| Measurement | 1.8.1 baseline | Candidate | Interpretation |
| --- | ---: | ---: | --- |
| App private memory, controlled same-history UI test | 81.8 MiB | 41.6 MiB | About 49% lower; temporary OCR child processes excluded |
| App working set, same controlled test | 102.3 MiB | 62.8 MiB | OS residency varies with the machine and workload |
| Isolated catalog process private memory | 52.5 MiB | 15.0 MiB after full lookup exercise | Catalog moved to disk; not a whole-app claim |
| Cold exact catalog lookup | In-memory reference | 1.54 ms median / 3.04 ms p95 | 71,050 valid catalog records checked; hot queries use a 256-entry cache |
| Total mask preprocessing, 166 comparisons / 83 saved frames | 7.82 s | 4.98 s | About 36% lower total elapsed time on this corpus |
| Median mask preprocessing | 20.44 ms | 21.35 ms | Median did not improve; gains concentrate on color-heavy frames |
| Mask output agreement | Reference | 0 mismatches / 12,655,674 source-pixel classifications | Pixel output unchanged for the replay corpus |

The paired app-memory test used separate hidden native UI processes, the same copied ledger and the same catalog, with tracking/network timers inactive. It measures a controlled idle state, not RAM while actively capturing a game. The isolated catalog benchmark includes its test harness. Timings are single-machine samples, not universal guarantees. Raw captures and copied ledgers remain local and are excluded from source and release artifacts.

## Changes retained

- Stream the JSON catalog into a separate, rebuildable SQLite index. Keep a bounded 256-name exact lookup cache instead of full Python name/token indexes. Failed imports retain the previous index. History stays in its original database.
- Resolve exact catalog identities before treating a short word prefix as icon noise. A regression covers Lion Meat versus Meat, along with duplicate event item IDs and quality variants.
- Classify each distinct pixel color once during the text-quality filter, then reuse the result. The retained algorithm produces the same masks in the private replay test.
- Skip repeated full-history refreshes when no ledger revision changed. Build a preview image and update the OCR text widget only while that panel is visible.
- Save a changed notification baseline immediately, with a 30-second heartbeat for unchanged baselines, rather than committing it on every frame. History rows still commit when recorded.
- Use a one-directory Windows build for fast startup. Exclude unused NumPy, SciPy, pandas, matplotlib, Torch and OpenCV. Tray dependencies and generated assets remain included. Tesseract is a separate installation and exits after each OCR call, avoiding a permanently loaded model.

## Verification and remaining work

118 isolated native regressions pass locally. The extracted Windows package is checked with a disposable profile: native widgets, bridge, bundled assets, history integrity, tray dependency import and a generated OCR fixture. The pipeline runs these checks before publishing a prerelease. A successful dependency import is not an end-to-end tray-restoration test against a live game.

Next performance work should measure whole-process-tree CPU/RAM during a labeled run, then compare bounded row caching and spatial row alignment against the same ground truth. Keep a change only when it improves a measured budget without adding false counts. Fast scrolling, unreadable text, identical retained lines and blocked capture can still miss items. No quantity is invented to fill a gap.
