# First-release review

## Release scope

The complete Windows product remains: saved loot/silver, crafting and grind sessions, paired planner, optional sharing, tray tools, Gear Studio and reviewed tooltip import. rc.4 adds optional alchemy Guild Quest and fixes automatic tool discovery. The working crafting timer's selection, time calculation and sending behavior are retained.

## Addressed release blockers

- Tool discovery failed against bright scenery and camera positions. Quote-noise could swallow TSV rows; a tight search band could clip labels; merged words placed numeric crops incorrectly. The reader now disables CSV quote interpretation, expands the search band and adds bounded gold-line/character-box localization with focused numeric consensus.
- A real missed capture now reads 2,910/3,000 plus its 3,000/3,000 neighbor. Another camera layout reads the active 2,287/3,000. Previously successful low counters remain replay regressions. Duplicate locators are merged; disagreements remain uncertain.
- Guild progress must not borrow personal quests or local loot totals. The parser scopes the alchemy guild objective and verifies its count in two reads. A real 184/600 widget excludes a neighboring 2/100 objective.
- Alerts must not repeat after restart or guess completion during outages. State and delivered flags persist, blocked/stale readings pause, and new-quest reset evidence is explicit.
- Saved history must survive builds and updates. Profile data stays separate, installs use the single-instance guard and verified backups, and loot rows are compared before/after updates.

## Efficiency and security

No new runtime dependency or resident service. OCR stays single-threaded at below-normal priority. Tool discovery has a six-second budget, bounded candidates and small field reuse. Guild tracking is optional/off by default, uses at most one short worker and shares the existing reader scheduling guard. Its crop/prepared-image budgets are explicit; no persistent images are enabled. Status routes are small, read-only and covered by the existing local origin restrictions.

The populated app still has meaningful background summary/price work. Prior paused-profile measurements were around 50 MiB private memory and 17% of one CPU core; this is not a zero-overhead or in-game FPS guarantee. Follow-up optimization should make completed-session summaries and price/catalog snapshots revision-driven. Recognition failures must remain visible rather than be hidden by guessed counts.

## Verification before delivery

Run the isolated native suite, planner syntax, gear core/security checks, saved tool/guild replays, native layout inspection, archive integrity and the extracted Windows OCR self-check. Record exact source identity in the packages and preserve old checkpoints. Keep real captures and profile data local. Native live changing-counter and camera checks add confidence; saved-frame and generated tests alone do not prove complete live coverage.

## Remaining limits to disclose

Unsigned Windows candidate; Tesseract English is still installed separately. Occluded/off-screen tool labels cannot be read. Overlapping names, unfamiliar zoom/fonts and clipped widget text can remain unresolved. Guild alerts require a visible readable objective; no actual guild completion was forced for testing. Icon-only gear recognition is still experimental. Public-first-release readiness depends on representative user testing, not a claim of perfect OCR.
