# Integrated platform release plan

Checked items mean implemented with automated evidence, not universal live-game acceptance. This plan preserves the user's complete scope; a candidate package is not proof that every unchecked item is finished.

## Current candidate: 1.13.0-rc.5

The integrated implementation includes Home, linked recipe-session economics, frozen assumptions, bounded gross/net graphs, persistent quiet goals and reviewed Fairy journal receipts. See [platform workflows](handbook/19-platform-workflows.md). Remaining unchecked live/visual criteria are not erased by packaging this candidate.

## Current acceptance blocker: readers and diagnosis

User reports tool discovery still fails and guild OCR works only intermittently. These are open product defects despite prior regression passes. Current replay evidence: private unobstructed live frame failed tool discovery before the low-fill/dark-track fix; the same frame then reads 635/3000 and 917/3000 and selects 635 by Place Mode (~2.24s). Guild replay reads 58/600 and Daily98/100. A second screenshot contains the Vision window over part of the game and is not proof of a valid timed tool comparison. Live diagnostics also report foreground loss and quest occlusion. Live end-to-end confirmation after installation remains required.

- [x] Full-size source image, hold capture, bounded attempt history and repeated-error suppression in both reader viewers.
- [x] Quest preview delivered before OCR and partial pass output retained on later failure.
- [x] Tool failure trace retains readable token text/geometry instead of truncating to TSV boilerplate.
- [x] Low-fill tool bars on gray backgrounds have a synthetic regression.
- [x] Reject conflicting full-label/bar context even when both numeric passes or the pixel cache agree; test leading digits with real Tesseract at multiple sizes.
- [x] Large same-field drops schedule fresh discovery; suspicious downward identity changes require use evidence.
- [x] Filter texture-only gold candidates before OCR; keep independent numeric validation. Duplicate partial hints inside verified fields do not count as separate misses.
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
- [x] One activity/mode overview with all reader states visible together; scrollable Home and collapsed occasional Capture Setup.
- [x] Compact 380×560 main tracker, 860×650 workspace, smaller controls/debug previews, and collapsible advanced controls. Default main window area is about 61% smaller; this is UI area, not a CPU/RAM reduction.
- [x] Real native compact preview inspected; regressions check that primary scan/send/tray controls fit and advanced controls expand/collapse.
- [ ] End-to-end onboarding, setup recovery, keyboard, contrast, resizing and Windows scale checks.
- [ ] Remove remaining duplicate controls and unnecessary window switching.

## Crafting and valuation

- [x] Recorded daily output, rare units, event counts and gross market value.
- [x] Explicit daily ingredient spend, sale retention and other expenses; withhold unsupported profit.
- [x] Detailed recipe-planner route remains available.
- [x] Link the selected existing recipe, observed outputs and planner yield/tax/expense assumptions to a crafting session.
- [x] Derive modeled material quantities/costs from exact existing quotes; missing quotes withhold net value. Actual batch count/inventory consumption is not measured.
- [ ] Reconcile actual material inventory consumption and actual yields when independent evidence exists; do not describe a yield model as measured consumption.
- [x] Separate recorded gross, modeled tax/material expenses and net; retain manual daily budget as an independent scope. Purchasing cash is not a measured transaction.
- [x] Craft session summaries alongside daily totals; freeze session model/material quotes at finish.

## Graphs and rewarding feedback

- [x] Bounded cumulative craft curve, top-item bars, recorded-output milestones.
- [x] Session gross/profit graphs with observed/excluded time and honest rates; 48-point native rendering.
- [x] Integrated grind and rare-drop summaries with shared accepted ledger quantities.
- [x] Persistent daily unit goals and deduplicated lifetime achievements; quiet static feedback needs no motion toggle.
- [ ] Fair personal-best comparisons, configurable celebrations and complete accessibility acceptance.
- [x] No achievements based on invented drops or guessed quest credit.

## Lite Use and efficiency

- [x] Initial current-tool durability only, then estimated timer; loot/quest/gear OCR paused.
- [x] Preserve tracking options; discard pending loot/quest results on mode transition.
- [x] No new native OCR or graph dependencies for platform integration.
- [x] Lite transition publishes pause once; subsequent ticks skip capture checks, quote refresh, ledger publication and session writes.
- [x] Home totals aggregate in SQLite; shared completed grind history is bounded to 30 runs.
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
- [x] Reviewed native completed-run journal receipts with stable history/session IDs, duplicate protection and failed-storage rollback. Unknown kills stay unknown; simulated sessions/ownership remain separate.
- [ ] Reviewed identity aliases for ambiguous treasure pieces and pity materials.
- [ ] Unified persistent platform navigation and progress presentation after visual review.

## Preserve and verify existing features

- [x] Regression suites cover loot parsing/deduplication, ledger, silver, clocks, timers and optional sharing.
- [x] Regression suites cover quests, grind sessions, gear rules/import, tray and bridge security.
- [x] Protected profile, verified backups, separate application files and immutable older packages.
- [ ] Live combined walkthrough verifies those features together rather than treating unit coverage as live proof.
- [x] Document current implementation, assumptions and extension contracts in linked handbook chapter 19 and quick start.
- [ ] Complete candidate visual/live QA; do not equate unit tests with a combined walkthrough.
- [ ] Final release package, source backup, history comparison, rollback and clear launch instructions.

## Bird's-eye dependency order

Visible BDO -> bounded OCR -> verified observations -> one ledger/session model -> identity and price resolution -> economics -> graphs/goals. Fairy Codex reads the same accepted observations; it does not create a competing loot ledger. Owned treasure progress remains a separate user decision. Lite Use gates capture upstream, so every downstream view must show paused/last-known observations rather than simulate new facts.

Finish observation reliability and session contracts before extending rewards. Finish integration and live acceptance before calling this complete production readiness. Developer tools and documentation stay outside the gameplay runtime.
