# BDO Vision Lite changelog

## 1.13.0-rc.6 · fragmentary bar confidence

- Keep short/transparent dark-track fragments usable as label locators without trusting their distorted fill percentage.
- Recovered the saved near-empty 353/5000 tool frame; numeric agreement and established discovery remain unchanged.
- Added the fragmentary-track regression and retained the compact rc.5 interface.

## 1.13.0-rc.5 · compact tracker and cheaper discovery

- Reduced default main/workspace sizes, spacing, buttons, debug previews and heading sizes; advanced main controls expand on demand.
- Separated the main layout into readable main_ui.py without changing timer, planner, tray or reader callbacks.
- Skip texture-only gold candidates before OCR and suppress duplicate partial-field miss messages; numeric consensus/context guards remain.
- Fixed Windows LF/CRLF generation differences in the reproducible Fairy page.

## 1.13.0-rc.3 · integrated platform candidate

- Unified Home with reader/session states, daily goals and persistent deduplicated milestones; collapsed occasional capture setup.
- Linked recipe session output, existing exact quotes and planner yield/tax/expense assumptions; frozen receipts and bounded gross/net graphs.
- Guarded numeric OCR/cache against fresh context conflicts and suspicious drops without inventing digits or adding regular OCR passes.
- Added reviewed, deduplicated Fairy journal receipts; retained unknown kills and separate collection ownership.
- Reduced repeated Lite-mode work, used SQLite Home aggregates and bounded shared run history; no additional runtime dependency.
- Isolated development/test histories and documented platform editing contracts in handbook chapter 19.
- Read visible version from the shipped VERSION file; reject packaged identity mismatches.

## 1.12.1-rc.1 · OCR inspection and developer edition

- Added opt-in Tool and Quest OCR image/text inspection with no independent capture loop or screenshot logging.
- Rejected empty/unverified Place Mode selections and conflicting nearby-tool timed confirmation.
- Added two-pass focused guild-body recovery for wrapped counters within the existing work budget.
- Added disposable development launches, targeted isolated tests, contributor instructions and an offline searchable handbook with source atlas and generated contract references.
- Preserved stable 1.12.0 artifacts, protected profile/history, sharing, planner and tray behavior.

## 1.0.0 · First focused release

- Built a compact dark-violet timer dashboard and custom icon.
- Simplified Scan & Track → Send Now → linked planner workflow.
- Added a guided first launch: calibrate OCR region before enabling auto-scan.
- Removed intrusive planner tab switching and repeated notifications during auto-sync.
- Corrected comma-grouped durability parsing and confirmed downward-jump tool recognition.
- Prevented settings window from covering the game during region selection.
- Distinguishes local bridge readiness from browser-acknowledged sync.
- Added scrollable Settings with persistent Save control.
- Reduced launcher dependencies: Pillow is required; tray UI automation is optional.
- Added release regression tests and build workflow.

See `RELEASE_NOTES.md` for detailed testing and limitations.
