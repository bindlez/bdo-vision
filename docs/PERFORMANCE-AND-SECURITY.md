# Performance and security release pass · 1.11.1

## Implemented

- Share color/palette analysis across the three text-feed masks; avoid unused popup grayscale allocations for text feeds.
- Use one thread per short-lived Tesseract worker and below-normal Windows priority. This bounds OCR scheduling pressure; it is not a guaranteed speedup on every frame.
- Reuse a byte-identical, completely recognized text feed for up to 15 seconds. The cache holds at most three results, retains no image, and bypasses uncertain/empty reads, popup feeds, diagnostic recording and changed scan contexts. Cached readings still go through overlap deduplication.
- Save OCR screenshots/log files only when the user enables diagnostic recording. Live preview and recognized text remain available.
- Back off blocked/off loot polling; avoid enumerating all desktop processes when BDO is already foreground, retaining coverage checks.
- Suppress unrelated automatic tool scans while grinding with no running tool timer. Manual scans and crafting mode remain available.
- Reject accidental oversized loot selections: at most 750,000 pixels per feed and 1,000,000 combined. Valid crops are not downsampled to meet the limit.
- Bind the bridge to loopback, validate Host and exact paired origins, refuse opaque/sandboxed origins, and add framing/content-type protections. Standalone file planners must use the paired app page for personal APIs.
- Bound bridge requests to eight concurrent workers; time out stalled headers/bodies; reject ambiguous body lengths, unsupported encodings, non-finite and over-nested JSON.
- Escape market names and notification text before HTML rendering. Add automated hostile-text checks to CI.

## Measurements and limits

Compared with the preceding 1.11.0-rc.3 source on this Windows machine:

| Check | Before | After |
|---|---:|---:|
| Three-mask preparation, median across 83 saved frames | 47.50 ms | 28.92 ms |
| Mask CPU time, sum over those frames | 4,609 ms | 2,891 ms |
| Full loot reading, median across eight spread-out frames | 579.01 ms | 542.95 ms |
| Hidden full app, tracking off, one-core CPU over ~20 seconds | 0.77% | 0.70% |

All 249 mask comparisons were byte-identical. All eight compared OCR results retained identical events, ordered slots and empty/recognized flags; this establishes behavior preservation on those samples, not perfect accuracy. Idle measurement used empty disposable profiles and disabled market network activity. Candidate median private memory was 35.39 MiB and working set 60.89 MiB; loaded history, visible tables, catalog state and OCR child processes change memory use.

A separate four-sample, single-frame OCR child test found similar wall times (~191 vs ~189 ms) and no CPU-time benefit from the one-thread setting on that small input (~172 vs ~180 ms median). Thread limiting is retained as a resource bound, not advertised as a universal efficiency gain.

No in-game FPS benchmark was performed. This release does not claim zero overhead, zero misses, or dependency-free OCR. General OCR remains Tesseract-based; the small native reader and icon matching remain separate experiments. Private capture/benchmark inputs stay local and are not bundled or uploaded. Regression reports and the extracted Windows check accompany the release library.

## Recovery and privacy

App updates retain the protected profile and create verified SQLite backups. The app never uses gear imports or projections to fabricate saved loot. Diagnostic recording is local and optional. The bridge is intended for the paired browser and native app on the same computer; it does not protect against malicious software already running as your Windows user. No new account, public backend or remote access service is introduced.
