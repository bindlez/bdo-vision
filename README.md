# BDO Vision 1.10.0-rc.1 — Crafting Studio

Adds material costs and modeled net profit, yield/timing assumptions, exact recipe market quotes, inventory-aware recursive shopping, production plans, comparisons, graphs and recorded-silver goals. Optional blocked-capture projections stay separate from confirmed loot and apply only to crafting.

The Windows app keeps the existing OCR, tray controls and protected history. No new runtime or chart dependencies. Timer valuation was about 79% faster on a synthetic 100,000-event ledger; this is not a live OCR accuracy or whole-app memory claim. See [features, measurements and deeper code review](docs/CRAFTING-STUDIO-REVIEW.md).

127 Windows regression tests, JavaScript checks and an extracted-EXE OCR check are required for this unsigned friend-test candidate. The public crafting demo uses example data and no live screen access.

## Previous release: 1.9.0-rc.1

# BDO Vision 1.9.0-rc.1 — lean friend-test candidate

The Windows ZIP includes the application and Python runtime. Extract it, open **OPEN-BDO-VISION.bat**, and follow **START-HERE.md**. Tesseract English is required separately. The build is unsigned and intended for a friend test before a stable release.

Measured changes reduce private app memory by about 49% in a controlled same-history idle test and mask preprocessing total time by about 36% on a saved-frame replay, with identical masks. See [measurement details and limits](docs/PERFORMANCE-RC1.md). The browser demo uses simulated data and does not perform native OCR.

118 local regression tests pass. History remains in the protected profile. The 1.8.1 baseline is preserved in Git and its prior ZIP.

## Previous release: 1.8.1

This release improves reading of the personal obtained-item message feed during grinding. Use Text feed, select 6–8 complete personal loot-message rows, and keep that part of the game visible. The target scan interval can be set to 0.5 seconds; actual OCR time and capture gap are displayed. Uncertain quantities and lost scrolling overlap are shown and excluded automatically. No manual loot corrections are required.

This source release requires Python, Pillow and Tesseract; it is not a standalone executable. See [release findings and improvements](docs/RELEASE-1.8.1.md) and [version control and recovery](docs/VERSION-CONTROL.md). Public source generates branding and synthetic OCR fixtures with `python scripts/generate_assets.py`.

For 1.8.1, 113 isolated native Windows regressions and the planner JavaScript syntax check passed locally. The previous release's validation details below remain historical evidence; GitHub CI results are reported separately.

## Open the app
Use the BDO Vision desktop shortcut. INSTALL.bat installs the application files and creates that shortcut. RUN.bat also works from the project. Opening another updated copy restores the same running app rather than creating another ledger.

## Your history
History, preferences, market quotes and sessions are saved in %USERPROFILE%/.bdo-vision, outside ZIP/extraction folders. Startup and updates create verified SQLite backups. Settings includes Back up history. Earlier recovered installation histories remain separately archived so overlapping game captures are not counted twice. The prepared local installation uses your recovered working history. A clean release does not include personal data; it automatically uses the existing protected profile on your PC.

## Silver and active timers
Optional sharing remains off for a fresh user and preserves existing preferences on upgrade. With sharing enabled, the website's active craft timer measures new recorded drops from the point it attaches, not your entire daily history. It shows market value, silver per observed hour, observed time, excluded time, and the formula. A single timer owns the live earnings measurement. Frozen timers retain their last recorded results.

Recorded value = sum(new captured quantity x matching market or verified NPC unit value).
Silver/hour = recorded value / observed seconds x 3,600 (after 60 observed seconds).

Blocked, minimized, stale, unreadable and offline capture time is excluded from observation. Readable periods with zero drops still count. Missing drops are not estimated. The craft countdown is a separate estimate of game progress and continues while earnings measurement is paused. Market value is before costs and fees, not a confirmed sale or net profit. Unpriced items are excluded from a labeled partial total. Unlisted loot uses a published NPC sell value from BDO Codex only when both item ID and item name match. Vendor values are labeled separately, cached locally, and never replace an available Central Market quote. Items without a verified value remain unpriced.

## Grind tracker
Use the Grind tab in Vision, or Vision Grind Tracker on the website. Start a named spot/route, pause/resume and finish a run. Both surfaces control the same saved session. Captured loot feeds the run automatically. Results include observed-time silver/hour, excluded time and coverage, rare-notice units, loot pulse, run history and optional treasure-pursuit progress. Three completed runs at the same spot unlock a personal median benchmark. The website exports CSV and a purple/black PNG recap; the native app exports session CSV. Nothing is uploaded automatically.

## Capture quality
Item names are checked against the downloaded item database. Unmatched screen text is retained in read-only diagnostics and excluded from new loot counts. Recent notification baselines survive restarts to reduce duplicate popups. Normal/rare elixir variants remain separate. OCR is observational: short-lived or unreadable drops can still be missed, and capture gaps reduce coverage. English client text is currently supported.

## Preserved features
The existing recipe catalog, ingredient view, Central Market interface, durability OCR, planner bridge, timer, tray controls and recorded session history are retained. No separate editable-price system was added.

## Validation
108 isolated Python regression tests passed, including real native widget construction, screenshot OCR fixtures, identity matching, optional sharing, capture clocks, timer ranges, session price snapshots, duplicate-popup recovery, persistent-profile migration and website commands applied to the native controller. Planner scripts compile. An isolated browser test verified 297,200 silver from five new sample drops, exclusion of older history, covered-capture pauses, expanded formula stability, grind controls, treasure progress and saved recap data. Synthetic browser-test data never enters the real profile.
