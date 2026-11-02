# BDO Vision · current development candidate 1.13.0-rc.11

**CP Intelligence** compares byproduct cash exchanges, CP gains and target/split routes using the current CP EXP curve and existing Central Market quotes. Native CP Info and the full browser planner show EXP to next/target CP, whole-batch allocations, opportunity cost, deployment assumptions, break-even and lightweight graphs. [Open the interactive offline preview](demo/bdo-vision-cp-demo.html). The optional one-shot CP HUD reader requires two-pass agreement and adds no background scanning. See [the CP developer guide](docs/handbook/21-cp-intelligence.md) for data provenance, arithmetic and limitations.

**Big Drops** turns accepted rare loot into a local trophy journal: Big for individual quoted items over 1B, Huge over 10B, and curated treasure recognition regardless of price. The native tab and shared website show item details, personal observed rarity comparisons and a retrospective heat rating. No new OCR, polling service, network request or chart dependency is added. Try the [interactive sample preview](demo/bdo-vision-big-drops-demo.html); its data is synthetic. See [the Big Drops editing guide](docs/handbook/20-big-drops.md) for rules, data limits and tests.

Lite Use reads the current tool once, includes an optional paired last-seen quest snapshot, then stops all OCR. Normal mode stops tool OCR after confirmed crafting use until the countdown reaches zero. A missed active-tool match no longer pauses an established estimate. Guild quests read only with tool attempts and stay last seen; loot follows its own setting outside Lite Use. **SCAN & TRACK** intentionally starts a fresh acquisition. These timers assume continued crafting at the configured pace.

The current candidate recognizes the guild's completed reward widget and shows **Guild quest: Complete** in the native app and frozen planner receipts. It preserves the actual last numeric counter. Bounded camera-angle fallback also recovers active-tool text above Place Mode against stone walls. See [candidate evidence](docs/CANDIDATE-VALIDATION.md) for measured scope and remaining live checks.

The published first release is [v1.12.0](https://github.com/bindlez/bdo-vision/releases/tag/v1.12.0). This candidate connects Home, Workshop, Grind, Sessions and Fairy Codex, adds recipe-linked session economics and bounded graphs, and rejects numeric tool readings that conflict with fresh independent context. Tool and quest debugging retain their actual images and decision evidence. See [integrated workflows](docs/handbook/19-platform-workflows.md) and the [acceptance checklist](docs/PLATFORM-RELEASE-PLAN.md) for supported behavior and remaining live checks.

For development start with [Start here](docs/handbook/01-start.md), run `python dev.py doctor`, then `python dev.py run` for a disposable profile. Build the linked, searchable website with `python dev.py docs` or open **DEVELOPER-HANDBOOK.bat**. Run `python dev.py check` before a release. The handbook includes line-linked source, schema references, feature editing guides, testing, profiling, releases and recovery. No developer tooling runs during normal gameplay.

Tool and Quest windows each have **LIVE OCR READER**. Previews reuse the existing scan and remain in memory only while open. OCR can still reject unreadable or overlapping text; these views expose the image, recognition and decision rather than promising perfect accuracy. Published packages and real history remain separate from development profiles.

The sections below are historical release notes; their defaults and validation describe those older versions.

# BDO Vision 1.12.0-rc.5 — automatic tools and alchemy Guild Quest

Focused gold-heading recovery handles the live near-complete widget as well as the initial reading. The real 184 → 593/600 sequence triggers one near alert; repeating the same frame does not alert again. Counter consensus, guild context and the three-second work budget remain required.

Adds an optional Guild Quest tab with verified objective progress, a default 90% warning, completion alert, recent observed pace and persisted alert state. Default widget discovery needs no selection; a custom area supports moved layouts. Hidden/unreadable objectives retain last verified values. No guild credit is inferred from loot. See [Guild Quest](docs/GUILD-QUEST.md).

Automatic tool discovery now supplements the label band with bounded gold-bar/character-box searches, reads difficult merged numeric fields and fixes quote handling in OCR rows. The crafting timer behavior is retained. See [release readiness](docs/RELEASE-READINESS.md) for evidence and limits.

## Previous candidate: 1.12.0-rc.3

Also shares background game-window discovery for five seconds while rechecking identity and coverage each time. Foreground game detection remains immediate. Unchanged Silver tables and disabled buttons avoid redundant UI updates. No extra process or dependency is added.

Verified counters appear immediately in the main window, before active-tool confirmation. VIEW TOOLS explains finding, confirming, tracking and paused states with reading ages and a small local status export. Camera checks avoid long retry chains; focused numeric results have a bounded eight-second exact-pixel cache. No extra background service or dependency is added. See [automatic tools and measured limits](docs/AUTOMATIC-TOOLS.md).

## Previous candidate: 1.12.0-rc.1

Cooking/alchemy durability no longer needs an initial capture box. The character anchor prioritizes visible labels, Place Mode is a fallback, focused numeric OCR verifies counters, and repeated durability use identifies the active tool. Camera movement triggers reacquisition. See [automatic tools and limits](docs/AUTOMATIC-TOOLS.md). The complete loot, silver, crafting, grind, gear and history product remains included.

## Previous release

# BDO Vision 1.11.1 — ready to grind and craft

The complete Windows tracker: saved loot and silver, grind sessions, crafting intelligence, tray tools and Gear Studio. Start with [the short setup guide](docs/QUICK-START.md); see [measured performance and security changes](docs/PERFORMANCE-AND-SECURITY.md) and [releases, checkpoints and recovery](docs/RELEASE-SYSTEM.md). The Windows ZIP includes Python; live OCR still requires Tesseract English.

This maintenance release preserves the existing protected profile. Normal operation no longer writes OCR screenshots to disk, unrelated tool OCR stays idle during grinding, and the local planner uses a bounded, origin-checked connection. No zero-FPS-impact or perfect OCR guarantee is made.

## Previous equipment-import candidate

# BDO Vision 1.11.0-rc.2 — clearer equipment import

Fixes from the first real sweep: read titles beyond sparse-OCR scene noise; understand `PEN: Item` and named Slumbering Origin ranks; preserve complete tooltip headers near screen edges; and retry uncertain reads on the tooltip header itself. Verified Kharazad identities from the local item index can now be imported and edited without pretending they have Central Market prices. All changes stay in gear import/planning; the working loot reader and existing tracker features are preserved. See [the rc.2 import audit](docs/GEAR-IMPORT-RC2.md).

## Previous candidate: 1.11.0-rc.1 — Gear Studio

The full app now includes Gear Studio: real market equipment, separate equipped/target sets, enhancement-specific quotes, independent accessory slots, upgrade budgets, saved builds and Windows/JSON backups. Open GEAR STUDIO from the native app or planner sidebar. Existing silver, crafting, sessions, grind, loot OCR and tray features remain available.

Start a three-second clockwise tooltip sweep, switch to BDO and hover over your items. Review names, enhancement levels and slots before applying; unknown items stay unresolved. Capture and OCR run locally only when requested. A generated tooltip image passes real OCR testing; live sweep validation across real equipment layouts is pending. See [Gear Studio](docs/GEAR-STUDIO.md) and the [Cloudflare backend plan](docs/BACKEND-PLAN.md). Market prices do not provide verified AP/DP curves; full stat simulation is not claimed.

## Previous extraction audit candidate: 1.10.0-rc.3

A wider extraction audit found and fixed malformed quantity handling, mixed-message omissions, bundle names containing xN, failure words inside valid item names, and harmless OCR punctuation around personal notifications. Existing captures, OCR masks, consensus rules, crafting tools and protected history remain unchanged.

141 Windows regression tests include matrix and scrolling checks. The full audit additionally checks 59,372 catalog names and 83 saved frames. Image recognition still has measurable misses: see [the extraction audit and its limits](docs/EXTRACTION-AUDIT.md). This candidate does not claim perfect OCR.

## Previous release: 1.10.0-rc.2

# BDO Vision 1.10.0-rc.2 — Crafting Studio

Adds material costs and modeled net profit, yield/timing assumptions, exact recipe market quotes, inventory-aware recursive shopping, production plans, comparisons, graphs and recorded-silver goals. Optional blocked-capture projections stay separate from confirmed loot and apply only to crafting.

The Windows app keeps the existing OCR, tray controls and protected history. No new runtime or chart dependencies. Timer valuation was about 79% faster on a synthetic 100,000-event ledger; this is not a live OCR accuracy or whole-app memory claim. See [features, measurements and deeper code review](docs/CRAFTING-STUDIO-REVIEW.md).

128 Windows regression tests, JavaScript checks and an extracted-EXE OCR check are required for this unsigned friend-test candidate. The public crafting demo uses example data and no live screen access.

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
