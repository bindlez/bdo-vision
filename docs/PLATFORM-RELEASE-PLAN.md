# Integrated platform release plan

Checked items mean implemented with automated evidence, not universal live-game acceptance. This plan preserves the user's complete scope; a candidate package is not proof that every unchecked item is finished.

## Current acceptance blocker: readers and diagnosis

User reports tool discovery still fails and guild OCR works only intermittently. These are open product defects despite prior regression passes. Current replay evidence: private unobstructed live frame failed tool discovery before the low-fill/dark-track fix; the same frame then reads 635/3000 and 917/3000 and selects 635 by Place Mode (~2.24s). Guild replay reads 58/600 and Daily98/100. A second screenshot contains the Vision window over part of the game and is not proof of a valid timed tool comparison. Live diagnostics also report foreground loss and quest occlusion. Live end-to-end confirmation after installation remains required.

- [x] Full-size source image, hold capture, bounded attempt history and repeated-error suppression in both reader viewers.
- [x] Quest preview delivered before OCR and partial pass output retained on later failure.
- [x] Tool failure trace retains readable token text/geometry instead of truncating to TSV boilerplate.
- [x] Low-fill tool bars on gray backgrounds have a synthetic regression.
- [ ] Verify the installed fixes over changing live counters and camera movement; do not call replay alone verified live reliability.

## Observation and tool reliability

- [x] Tool reader image, raw text and decision evidence; dashboard access.
- [x] Diagnostic capture survives OCR timeout; comparison input available.
- [x] Place Mode first selection, conservative numeric agreement and repeated-use confirmation.
- [x] Empty/tied/conflicting-neighbor rejection and bounded expanded anchor search.
- [ ] Live matrix: overlapping labels, moved camera/window, scale changes, identical tools, refills and replacements.
- [ ] Measure detection latency, incorrect selections and missed reads; address remaining failures.
- [x] Guild/Daily/Bonus debug view; retain working guild recognition unchanged in this integration.

## Unified interface

- [x] Main navigation to Workshop, Grind, Loot reader, Gear, Quests and Fairy Codex.
- [x] Native Crafts tab populated, scrollable, with useful empty-state guidance.
- [x] Observed, estimated, unknown and stale values remain distinct.
- [ ] Complete screen-by-screen consistency audit: fonts, spacing, terminology, controls and next actions.
- [ ] One activity/mode overview with all reader states visible together.
- [ ] End-to-end onboarding, setup recovery, keyboard, contrast, resizing and Windows scale checks.
- [ ] Remove remaining duplicate controls and unnecessary window switching.

## Crafting and valuation

- [x] Recorded daily output, rare units, event counts and gross market value.
- [x] Explicit daily ingredient spend, sale retention and other expenses; withhold unsupported profit.
- [x] Detailed recipe-planner route remains available.
- [ ] Automatically link recipe, batches, actual yields, normal/rare output and byproducts to a crafting session.
- [ ] Derive actual material consumption/costs from existing recipe and market data.
- [ ] Clearly separate purchasing cash, material value, gross proceeds, tax and modeled profit across native/web views.
- [ ] Craft session summaries alongside daily totals.

## Graphs and rewarding feedback

- [x] Bounded cumulative craft curve, top-item bars, recorded-output milestones.
- [ ] Session gross/profit graphs with observed/excluded time and honest rates.
- [ ] Integrated grind and rare-drop summaries.
- [ ] Persistent personal goals, achievement deduplication and fair personal-best comparisons.
- [ ] Optional quiet celebrations, reduced motion and accessibility checks.
- [x] No achievements based on invented drops or guessed quest credit.

## Lite Use and efficiency

- [x] Initial current-tool durability only, then estimated timer; loot/quest/gear OCR paused.
- [x] Preserve tracking options; discard pending loot/quest results on mode transition.
- [x] No new native OCR or graph dependencies for platform integration.
- [ ] Live mode-switch and new-tool workflow acceptance.
- [ ] Comparable CPU/memory/capture/subprocess benchmarks for idle, initial scan and active tracking.
- [ ] Hidden-screen redraw and polling audit across every feature.
- [ ] Deferred full efficiency rebuild; no two-thirds cost reduction claimed.

## Fairy Codex

- [x] Verify latest main: V36.1 at 99633c300ea69e06d111fdd54d9b493ab0a01bd2.
- [x] Preserve upstream source separately; deterministic adapter/build.
- [x] Same-origin local page, native and planner navigation, inclusion in packages/install.
- [x] Optional recorded-loot snapshot, exact treasure-name matches, bounded rendering and visible-page polling.
- [x] Keep observed drops separate from owned inventory, pity conversion and collection completion.
- [x] Preserve Fairy vault/profile keys; document origin-specific export/import.
- [ ] Browser/live verification of existing simulations, imports, loot linking, disconnection and Lite Use.
- [ ] Native-to-Fairy session import with stable IDs and deduplication.
- [ ] Reviewed identity aliases for ambiguous treasure pieces and pity materials.
- [ ] Unified persistent platform navigation and progress presentation after visual review.

## Preserve and verify existing features

- [x] Regression suites cover loot parsing/deduplication, ledger, silver, clocks, timers and optional sharing.
- [x] Regression suites cover quests, grind sessions, gear rules/import, tray and bridge security.
- [x] Protected profile, verified backups, separate application files and immutable older packages.
- [ ] Live combined walkthrough verifies those features together rather than treating unit coverage as live proof.
- [ ] Update handbook/quick start to final accepted behavior and complete visual QA.
- [ ] Final release package, source backup, history comparison, rollback and clear launch instructions.

## Bird's-eye dependency order

Visible BDO -> bounded OCR -> verified observations -> one ledger/session model -> identity and price resolution -> economics -> graphs/goals. Fairy Codex reads the same accepted observations; it does not create a competing loot ledger. Owned treasure progress remains a separate user decision. Lite Use gates capture upstream, so every downstream view must show paused/last-known observations rather than simulate new facts.

Finish observation reliability and session contracts before extending rewards. Finish integration and live acceptance before calling this complete production readiness. Developer tools and documentation stay outside the gameplay runtime.
