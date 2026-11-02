# BDO Vision · crafting platform execution brief

This is the organized working prompt for the user's November 2, 2026 request. It also preserves the unfinished release work from the preceding CP/tool/quest tasks. Check a task only when its evidence exists. Continue implementation after this brief; it is not an approval gate.

## Working prompt

You are developing BDO Vision into a coherent, lightweight Windows companion and local browser platform. First stabilize and preserve the current release. Then audit the whole application, simplify genuinely redundant code and confusing UI, and build a complete cooking, alchemy and processing planning system informed by the public functions of BDolytics at `https://bdolytics.com/en/crafting?category=alchemy`.

Treat accurate recipes and current item identities/prices as shared platform infrastructure. These calculators are the core for CP decisions, crafting profits, session analysis and other features. Research and document the reference calculator before claiming parity. Implement original code and presentation; do not copy another site's proprietary implementation or branding. Preserve every working user-facing feature and all saved history.

Expose the main workflow simply: choose an activity and recipe, set quantity and character assumptions, inspect materials and expected results, then start or save the plan. Keep advanced assumptions, subrecipe controls, taxes, detailed comparisons and diagnostics available through progressive disclosure. Add useful graphs and satisfying progress/milestones tied to clearly identified modeled or verified data. Never present a simulation as actual income or invent better drop odds.

Use the existing Central Market infrastructure for current prices, with exact item IDs, region, timestamps and incomplete-coverage states. CP's main cash comparison must value the materials received from byproduct exchanges at market prices. Direct NPC selling belongs in an optional alternative, not a headline fallback that hides unavailable market quotes. Verify the latest Clear Liquid Reagent quote rather than hardcoding the user's approximately 12,000-silver observation or an older cached price. Refresh deliberately and efficiently; “real time” must not imply an unsupported live tick feed.

Keep the Windows runner extremely frugal. Recipe browsing and calculation must not add ongoing OCR, game memory access, input automation, animation loops or unnecessary background services. Reuse caches and accepted observations, keep calculations bounded and lazy, and benchmark representative paths. Maintain the verified tool-timer hold, Lite Use, optional sharing, tray controls, loot/session history, Guild/Daily/Bonus observation rules, Big Drops, Gear and Fairy Codex.

Publish an evidence-based project paper as a website with Markdown as its canonical source. Use the requested imaginary first-person learning-human voice, explicitly labeled as fictional narrative based on actual project notes. Explain architecture, failures, accuracy, optimization, UI design, integration, validation and lessons. Cite sources, distinguish measurements from hypotheses, and publish no personal captures, profiles, chat logs, credentials or private loot history.

## Non-negotiable contracts

- `sources/` is read-only reference material. Real user history is never a test profile.
- Preserve immutable previous packages and checkpoint each meaningful release. Test the extracted standalone Windows build; do not replace its launcher with a Python-dependent source launcher.
- OCR uncertainty remains unknown. Two agreeing transforms are useful checks, not a 100% accuracy guarantee. Confirmed tool use holds automatic tool OCR until countdown zero. Lite Use stops optional extra readers.
- Prices come from the shared quote system. Show source, region and freshness; keep unknown prices explicit. No separate sample-price editor.
- Ingredient substitutions, enhancement/item variants, rare outputs, quantities and taxes must retain their meaning across calculators, CP and observed sessions.
- Actual ledger events, modeled yields and CP opportunity values are separate. Prevent double-counting byproducts, input costs, output value or overlapping sessions.
- Keep publication free of personal data. The paper's fictional narrator must not turn invented experiences, benchmarks or scientific credentials into factual claims.

## Ordered task list

### R0 · Finish the current checked release

- [x] Expand CP payoff analysis: ramp-up, uptime, setup cost, deadlines, stress cases, reserve-constrained targets, graphs and simulated recovery milestones.
- [x] Improve initial tool acquisition, fresh bar evidence and changing-digit geometry; preserve the established countdown.
- [x] Improve full-width wrapped quest cards, bounded reader handoffs, clear states and optional Smart watch.
- [x] Pass the full 370-test native suite, shipped JavaScript checks, graph interactions and handbook links.
- [x] Commit/checkpoint rc.12, package and verify Windows/source/handbook artifacts, back up the exact source remotely.
- [ ] Install only after Vision closes safely; verify a consistent backup and unchanged complete history. Use the standalone executable and retain the old releases.

### A1 · Audit and simplify before extending crafting

- [x] Inventory current modules, generated/owned assets, routes, data stores and calculator entry points.
- [x] Map every user-visible feature and its consumers before removing anything.
- [x] Identify redundant calculations, repeated quote/network work, duplicate UI flows, unused controls and obsolete code.
- [x] Distinguish intentional generated copies and offline/native parity implementations from accidental duplication.
- [x] Consolidate safely, preserve compatibility adapters where needed, and document actual removals and retained tradeoffs.
- [x] Run focused regressions and compare representative performance before/after. Keep this checkpoint reviewable.

### B2 · Research the reference and verify core data

- [x] Inspect cooking, alchemy and processing public calculator behavior; create a feature-parity matrix with source/date and verified/unknown status.
- [x] Identify public recipe data, item IDs, ingredient groups, substitutions, ordinary/rare/byproduct outputs and activity-specific rules.
- [x] Verify mastery, yields, mass production/processing, skill restrictions, craft time, sale tax and other assumptions from appropriate primary sources.
- [x] Audit the current bundled recipes for sample entries, missing data, wrong quantities or weak provenance.
- [x] Establish a dated, attributable, compact recipe dataset and exact market-item links, with bounded import/lookup behavior.

### C3 · Build the shared crafting engine

- [x] Add real cooking, alchemy and processing categories with fast search, useful filters and clear recipe details.
- [x] Calculate batches, ingredients, substitutions, yields, ordinary/rare outputs, byproducts, time, gross value, retained revenue, costs and profit.
- [x] Support inventory on hand, shopping shortages, craft-versus-buy decisions and bounded recursive subrecipes with cycle guards.
- [x] Support multiple plans, shared ingredient aggregation, useful exports and saved character/activity assumptions where justified by the reference matrix.
- [x] Keep unknown prices/yields explicit and provide explanations rather than invented precision.

### D4 · Use real exchange prices throughout CP

- [x] Match every Catalyst, Witch's Delicacy and Blush Leaf reward to the existing market database.
- [x] Fetch/use current region-correct quotes with visible timestamps and efficient cache freshness rules.
- [x] Promote market exchange outcomes to the main CP comparison. Move direct NPC sale into optional alternatives.
- [x] Keep batch leftovers, taxes, liquidity limits and missing-price coverage accurate; do not claim unavailable quotes are zero or a best route is complete.
- [x] Recompute CP opportunity cost, required income, payoff, splits and graphs from the same quote snapshot.
- [x] Keep offline demos clearly labeled as snapshots/examples; never pretend they have live Windows capture or a live market feed.

### E5 · Integrate with the platform

- [x] Link planned recipes to tool timers and native/browser handoffs without breaking current timer or tray behavior.
- [x] Link accepted crafted output, rare extras and byproducts to the active plan/session through exact identities and optional sharing.
- [x] Compare planned and observed results, with capture gaps and incomplete data clearly identified.
- [x] Reuse shared prices, taxes, recipe identities and cost assumptions across Crafting, Sessions, Loot, Silver and CP.
- [x] Make navigation and empty/blocked/loading states coherent. Preserve Gear, Fairy Codex and Big Drops.

### F6 · Graphs and gamification with a simple UI

- [x] Give the main view a small number of useful choices and a clear next action.
- [x] Add material/profit breakdowns, time/value projections, scenario comparisons and bottleneck views that answer real player questions.
- [x] Add meaningful milestones, readiness/recovery progress and rewarding session feedback; label simulated checkpoints separately from earned ones.
- [x] Keep advanced details expandable, controls keyboard-accessible and statuses understandable without relying only on color.
- [x] Avoid perpetual animations, noisy notifications and charts that recalculate while hidden.

### G7 · Write and publish the project paper

- [x] Create a canonical Markdown paper with the fictional-perspective note, abstract, methods, evidence, failures, lessons and limitations.
- [x] Cover low-cost OCR, current-tool selection, changing digits, wrapped quests, resource budgets, event-driven UI, recipe/pricing architecture, history safety and version control.
- [x] Use only defensible measurements and labeled experiments. Include reproducible benchmark scope and source links.
- [ ] Build a readable linked website and publish through the user's established hosting/repository workflow, with a stable link from the index.
- [ ] Keep the Markdown editable and ensure all local/source/public links work.

### H8 · Final validation and delivery

- [ ] Verify every row of the feature matrix and resolve unsupported or uncertain behavior explicitly.
- [ ] Test domain math, market identities, recipe substitutions/recursion, partial prices, session boundaries, OCR rejection cases and history-safe upgrades.
- [ ] Measure representative cold/warm calculation and reader costs; report limits without claiming zero FPS impact.
- [ ] Check the actual shipped HTML, native controls, demos and standalone Windows package.
- [ ] Deliver an accessible release, editable project, developer documentation, runnable demo and published paper; record exact versions/checksums and remaining live checks.

## Completion standard

The result must be usable, integrated and reviewable, with genuine recipes as its foundation. A plan, cosmetic mockup, sample recipe list, unpriced total presented as complete, or unverified claim of reference parity does not complete the task. Progress through this checklist autonomously; ask only for information or access that is actually missing, while continuing independent work.

## Evidence status for rc.13

Completed implementation rows above are scoped by `CRAFTING-REFERENCE-MATRIX.md`: public model assumptions and absent minimum-skill facts remain explicit; custom item-price editors and private cloud-account flows are intentionally excluded. The paper is built with 29 linked sections and editable Markdown. Final package/remote publication and installation rows stay open until their evidence exists.
