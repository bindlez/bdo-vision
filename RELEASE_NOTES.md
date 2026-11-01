# BDO Vision 1.12.1-rc.1 — OCR inspection and Developer Handbook

Tool Reader and Quests each include an optional Live OCR Reader showing actual input, recognized text and acceptance/rejection evidence. No extra scan loop or persistent screenshots are added. Tool position selection excludes empty/unverified fields; a changing neighbor cannot confirm a conflicting Place Mode choice. Guild fallback can read the focused objective in both wrapped layouts within its existing budget. Unreadable bright/overlapping text can still be rejected; this is not a perfect-accuracy claim.

Developer tools add isolated launches, selected tests and a linked offline handbook with source pages, symbol search, settings/schema references, feature recipes and release/recovery guidance. Build with `python dev.py docs`; use `python dev.py check` for the full development gate. The handbook is separate from the gameplay runtime. Existing published 1.12.0 packages are retained unchanged.

# BDO Vision 1.12.0 — first release

Includes immediate Place Mode-based selection from verified OCR, subsequent use confirmation, timed tool comparison, independent Guild/Daily/Bonus objective counts, wrapped counters, last-seen guild information on planner sends and protected history. Warnings default to guild 95% and ten seconds. Real reference captures cover numerator on either objective line. OCR can still fail over bright or overlapping text; unresolved values are labeled rather than invented. Live tool recognition was confirmed by the user and the running app at 2655/3000. Separate Tesseract English and visible readable game text remain required.

# BDO Vision 1.12.0-rc.10 — start from Place Mode selection

A verified counter near the Place Mode control starts the countdown on the first scan, before wear confirmation. The next scan is due after 1.5 seconds; repeated use or the timed comparison confirms selection. The native view distinguishes selected by position from confirmed by use. Equal-position ambiguity stays unresolved. All rc.9 quest objectives, last-seen planner receipts, warnings and history protection remain. OCR processing still takes time; this does not promise zero-latency recognition or perfect accuracy.

# BDO Vision 1.12.0-rc.9 — active-tool comparison and quest objectives

Tool discovery first checks a small residence header for Place Mode, then reads the label band relative to that control. Character and broad discovery remain fallbacks. When no tool is confirmed, two batches of known label crops are captured 1.5 seconds apart, before OCR. Every field must verify, title masks must stay stable, and exactly one plausible decrease may confirm an active tool. Changes to multiple tools, moved labels, missing fields and large jumps remain uncertain. The comparison shares the six-second work budget and has a fifteen-second cooldown; confirmed monitoring adds no pair. Images are transient crops, not a continuous full-screen recorder.

Quest parsing reads the whole objective block, allowing the numerator to move between its two display lines and allowing additional OCR line breaks. Daily and Bonus objectives have independent last-verified progress rows and completion alerts, using the same worker and bounded read budget. Focused title/body reads recover missing Daily/Bonus captions. Uncovered quest areas can be read while Vision is in front; covered or minimized areas pause. A due quest read gets a turn after existing reader work finishes. A refilled mission countdown plus two consistent reads can confirm a new guild mission without claiming the prior mission completed. Legacy saved missions from earlier builds migrate only after two consistent visible counters with their mission countdown; the previous partial snapshot is archived.

Sending a craft now includes a bounded guild receipt: last verified current/target, objective and timestamp. The planner timer labels it Last seen and never extrapolates quest progress. Optional loot-sharing behavior is retained.

Private saved captures verify both 13/600 and 184/600 placements, plus Daily 20/100 and Bonus 8/100 or 2/100. The Place Mode search recovers the 2623/3000 field in the latest camera layout. One saved bright-window JPEG still fails quest consensus and stays unverified. Real captures remain local; these regressions do not prove every background, resolution or live completion. Warning defaults remain 95% and ten seconds. Full efficiency rebuild remains deferred.

# BDO Vision 1.12.0-rc.8 — right-side guild counter punctuation

Warnings default closer to completion: guild quest at 95%, tool timer at 10 seconds remaining. Both remain editable.

The follow-up live test showed 525/600 on both the yellow notice and the right-side objective. OCR of the white counter produced an unmatched opening quote after the slash. The scoped counter pattern now accepts that separator punctuation while retaining literal digits, strict numeric boundaries and the existing two-pass consensus. Captured 362/600 and 525/600 both read successfully; damaged goal digits remain rejected. The estimate column, durability reader, timer and loot behavior are unchanged from rc.7. No separate yellow-notice scanner is added: it duplicates the right-side polling and has not shown a measured benefit worth more capture work.

# BDO Vision 1.12.0-rc.7 — tool-reader estimate column

Adds a clearly labeled estimated-durability column beside the verified value. For the confirmed active tool it subtracts whole uses since the existing last-read timestamp, using observed seconds/use or the configured craft speed. At one use/second this is verified durability minus integer seconds since read. Other tools retain their verified count. The estimate assumes crafting continues, including while capture is paused, clamps at zero and never becomes an OCR measurement or recorded loot. It uses the existing visible-window refresh and adds no scan, worker, polling timer or dependency. Tool recognition and the working crafting timer are unchanged. Includes the rc.6 guild separator fix.

# BDO Vision 1.12.0-rc.6 — small guild counter compatibility fix

The live test exposed a counter read as `362'//600`. Normalize only this separator punctuation inside the already scoped guild objective, preserving every digit and requiring the existing two-pass agreement. The same captured frame now reads 362/600; damaged digits, negative goals and three slashes remain rejected. Durability discovery, active-tool selection, timers and loot recording are unchanged from rc.5, which remains available as a fallback.

During the rc.5 live check the active tool retained its identity at 2240 then 2163/3000 and an empty neighbor was identified separately. This confirms that sequence; it is not a guarantee for every camera view. Guild live verification of rc.6 is recorded separately after installation.

# BDO Vision 1.12.0-rc.5 — recover difficult gold mission headings

The next real near-finish frame read 593/600 but lost the low-contrast gold guild heading. A bounded focused heading pass now supplies context only when it reads the alchemy guild caption, while both independent objective reads still have to agree. Narrow, harmless separator punctuation is normalized inside the scoped objective; damaged digits remain unresolved. The real 184 → 593/600 replay produces one near warning and no duplicate. New-quest 13/600 was observed separately; actual completion was not forced or assumed. rc.4 remains preserved in the local version library.

# BDO Vision 1.12.0-rc.4 — alchemy Guild Quest and automatic-reader fixes

Optional native Guild Quest tracking reads the visible alchemy guild objective, keeps saved progress, displays remaining units and observed pace, and alerts once near the configured percentage and once at completion. Default warning is 90%. Restarting does not repeat old alerts. New quests archive previous progress; an automatic reset after confirmed completion needs two separate readings. Defaults off, with no guild polling/worker while disabled. Default right-hand widget reads have an optional custom-area fallback, bounded crops, paired OCR consensus and short exact-frame reuse. No game inputs or inferred shared-guild credit are added.

The automatic tool reader fixes Tesseract quote parsing, uses a wider character-relative search band, supplements it with thin gold-line candidates and character-level number positions, and merges duplicate locators conservatively. Small crop alignment retries remain bounded. Conflicting counters remain unreadable, and partially hidden names stay unresolved. Saved live captures now recover 2,910/3,000 and 2,287/3,000 missed by the prior discovery path. Existing successful 2,890/3,000, 100/3,000, 95/3,000 and 82/3,000 readings remain regression targets. Crafting timers and their planner synchronization are preserved.

Actual guild-widget capture: Mysterious Catalyst 184/600 agreed in both OCR passes while nearby personal-quest 2/100 was excluded. Alert thresholds, persistence and resets are tested with generated data; this does not claim an actual guild mission was completed during testing. See docs/RELEASE-READINESS.md.

# BDO Vision 1.12.0-rc.3 — reduce paused/background work

The final installed-app check exposed repeated desktop-wide process searches from visibility consumers while BDO was behind other windows. A bounded five-second discovery cache now shares those results. Cached game identities are revalidated, current coverage is always checked, and foreground BDO bypasses negative results immediately. Tray restoration and keyboard helpers retain fresh discovery. Twelve background checks on this desktop fell from 133 ms / 125 ms CPU to 13 ms / 16 ms CPU, with identical unavailable results. This is a helper benchmark, not a total-app or FPS measurement. Silver tables no longer move every row when their content is unchanged; capture status still refreshes every second. All rc.2 reader and UI fixes remain included.

# BDO Vision 1.12.0-rc.2 — tool reader reliability and polish

Shows readable counters before a tool is confirmed, with explicit capture states, reading ages, a scrollable tool list and bounded local diagnostics. Reduces difficult-frame numeric retries, detects camera shifts from tiny title masks, handles split fraction tokens and retains identity through one missed frame without reporting a hidden tool as active. Two consecutive misses reset use evidence. Returning to BDO rechecks immediately; empty searches retry briefly before backing off. Main controls scroll on smaller windows. Existing loot, silver, crafting, grind, gear and history are preserved.

On three saved BDO frames, difficult reads fell from 13/17 OCR calls to 5/5; the candidate recovered an additional empty-tool counter. Identical cached fields took zero OCR calls during the eight-second cache window. This small replay is not a full accuracy or FPS benchmark; visible labels and separate Tesseract English remain required.

# BDO Vision 1.12.0-rc.1 — automatic durability and active tools

Adds automatic discovery of visible cooking/alchemy labels without drawing a region, a nearby-tools window, focused numeric consensus and active-tool evidence from repeated durability loss. Uses a character-based search prior and Place Mode fallback; reacquires after camera movement. Names and active identities remain unresolved when visual evidence is insufficient. New per-pass work bounds preserve the existing lightweight worker policy. Stable 1.11.1 remains available as a fallback.

# BDO Vision 1.11.1 — grind/craft performance and local security

Keeps the complete tracker and Gear Studio. Shares text-mask analysis, caps each OCR worker to one thread at below-normal priority, reuses only complete identical text reads briefly, makes screenshot diagnostics opt-in, rejects oversized capture selections and suppresses unrelated tool OCR while grinding. Tightens localhost origins and Host checks, bounds request workers/timeouts, rejects malformed bodies and escapes market text. Includes a short start guide, protected history and release evidence.

See docs/PERFORMANCE-AND-SECURITY.md for measured results and limits; no zero-overhead, perfect OCR or icon-only import claim.

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
