# BDO Vision 1.11.0-rc.3 — accessible Windows release and version library

Adds an on-demand local release library with downloadable packages, committed source identities, SHA-256 and complete manifest verification, clean-source checkpoints, testing instructions and profile-safe recovery guidance. Preserves the full tracker and reviewed tooltip Gear Studio. Icon-only equipment recognition remains an experiment outside this release. Tesseract English is still installed separately.

# BDO Vision 1.11.0-rc.2 — equipment import fixes

Removes the first-150-lines parser cutoff, accepts rank words without parentheses and Slumbering Origin adjective ranks, ignores description-only item mentions, and adds a focused tooltip-header retry. Edge-aware sweep captures preserve a full-height tooltip area at common resolutions, bounded to twelve 1280×1440 grayscale frames. A small verified Kharazad supplement uses exact local catalog IDs, retains 0–10 enhancement choices and remains explicitly unpriced. Named Slumbering Origin levels can remain editable during quote outages. No changes to loot OCR, counting, silver history, sessions, crafting or grind logic.

## Previous candidate: 1.11.0-rc.1 — Gear Studio

Adds a market-backed equipment builder to the existing full app, without replacing its loot, silver, session, crafting, grind or tray features. Equipment and target sets are separately editable; quotes use actual item IDs and enhancement intervals. Builds can be exported and explicitly backed up in the protected Windows profile, retaining a previous copy.

User-operated three-second tooltip sweeps capture a bounded set of pointer-adjacent frames, then run one on-demand OCR worker and show a mandatory review list. No automatic game input, screenshot upload or idle OCR polling is added. The separate native-reader lab is not the installed app. Live sweep coverage is still being tested; icon-only import and full AP/DP simulation are not claimed. Cloudflare Worker + D1 backend design is documented, not deployed.

## Previous candidate: 1.10.0-rc.3 — item extraction audit fixes

A wider extraction audit found and fixed malformed quantity handling, mixed-message omissions, bundle names containing xN, failure words inside valid item names, and harmless OCR punctuation around personal notifications. Existing captures, OCR masks, consensus rules, crafting tools and protected history remain unchanged.

141 Windows regression tests include matrix and scrolling checks. The full audit additionally checks 59,372 catalog names and 83 saved frames. Image recognition still has measurable misses: see [the extraction audit and its limits](docs/EXTRACTION-AUDIT.md). This candidate does not claim perfect OCR.

## Previous release: 1.10.0-rc.2

# BDO Vision 1.10.0-rc.2 — Crafting Studio

Adds material costs and modeled net profit, yield/timing assumptions, exact recipe market quotes, inventory-aware recursive shopping, production plans, comparisons, graphs and recorded-silver goals. Optional blocked-capture projections stay separate from confirmed loot and apply only to crafting.

The Windows app keeps the existing OCR, tray controls and protected history. No new runtime or chart dependencies. Timer valuation was about 79% faster on a synthetic 100,000-event ledger; this is not a live OCR accuracy or whole-app memory claim. See [features, measurements and deeper code review](docs/CRAFTING-STUDIO-REVIEW.md).

128 Windows regression tests, JavaScript checks and an extracted-EXE OCR check are required for this unsigned friend-test candidate. The public crafting demo uses example data and no live screen access.

## Previous release: 1.9.0-rc.1

# BDO Vision 1.9.0-rc.1 — efficiency and friend demo

Moves the full item catalog to a bounded-memory disk index, preserves exact item identities, reuses pixel-color classification, skips unnecessary hidden preview/history work, and reduces unchanged-baseline writes. Adds a one-directory Windows application, generated-art packaging, checksums and an extracted-application OCR check. The browser demo uses labeled simulated data.

See docs/FRIEND-TEST.md for setup and docs/PERFORMANCE-RC1.md for measured results. Tesseract is installed separately. This is an unsigned release candidate; remaining missed-loot cases require labeled live comparison.

## Previous release: 1.8.1

Improves outlined loot-message OCR on moving scenery, ordered message agreement, unreadable-row recovery and broken-quantity rejection. Loot scans no longer wait for durability OCR. A 0.5-second target is available, with actual capture/processing timing shown. Existing silver valuation, planner sharing, sessions, history and tray controls are preserved.

113 Windows regressions passed locally. See docs/RELEASE-1.8.1.md for findings, evidence and remaining limitations. Source packages include generated assets, a release manifest and SHA-256 checksum; personal captures and databases are excluded.

## Previous release: 1.7.1

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
