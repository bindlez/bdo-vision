# Simplification audit · November 2, 2026

The audit preceded the crafting expansion. It covered production Python modules,
browser entry points, generated assets, data stores, and calculator consumers.
The reference recipe research does not authorize replacing unrelated readers.

## What is shared

| Surface | Owners / dependencies | Preserved contract |
| --- | --- | --- |
| Windows timers, Lite, tray | app, tracking, main UI | Accepted timer holds; no extra polling |
| Tools / Guild / Daily / Bonus | tool reader, guild reader, common debug view | Bounded observations; unknown stays unknown |
| Loot / Grind / Big Drops | ledger, event parser, prices, sessions | Immutable captured quantities and provenance |
| Crafts / session economics | craft economy, recipes, shared PriceBook | Modeled costs separate from observed outputs |
| Browser plans / timers | crafting engine, Studio, timer adapter | Existing receipts and local storage retained |
| CP | Python/JS arithmetic, shared exchange data and prices | Native/offline parity; explicit simulations |
| Gear / Fairy | dedicated planners and optional bridge | Existing navigation and data retained |
| Release / handbook | versioned artifacts and generated site | Previous releases remain available |

SQLite user history and quote cache live outside the source tree. Browser plans
remain local to their origin. There is no new database or service in this cleanup.

## Actual simplifications

- Removed the quick-action Life Skill Profits implementation, which calculated
  one output per batch with separate fallback arithmetic. The same action now
  opens the existing Studio comparison, using its shared yield/tax assumptions.
- Added explicit ownership markers and a deterministic crafting builder for six
  previously hand-synchronized inline assets and recipe data. Developers edit one
  owned file, then regenerate the actual shipped planner.
- Extracted the recipe browser into its own owned asset. This separates recipe
  browsing from OCR upload, durability timing, and unrelated market rendering.

## Retained deliberately

The AST inventory found no exact duplicated Python function bodies. Python and JS
CP engines serve native/offline contexts and have parity tests. Embedded HTML and
demo copies are generated delivery artifacts, not redundant source modules.
Reader-specific OCR policies remain separate: combining their different acceptance
rules would risk weakening accuracy. The experimental native reader stays labeled
experimental. We did not remove features merely to reduce line count.

## Remaining findings driving the next change

114 recipes mix real entries, placeholder ingredient-group names and static fallback
prices. The browser has cooking/alchemy only; processing needs a real typed recipe
catalog. Several independent views assume one output per craft. Group substitutions
need replacement ratios, and queue stock must be consumed once across the queue.
CP currently allows NPC fallback in its default comparison; market-only comparison
must become the new explicit default, with incomplete quotes visible.

This is a scoped structural cleanup, not a claim that the entire codebase was cut
in half or that FPS, total memory, or OCR accuracy improved by a measured percentage.

## Follow-through in the crafting expansion

The Research profit form now delegates to Studio and no longer exposes separate sale-price/tax/yield arithmetic. Its saved historical snapshots remain preserved. Region changes rerender crafting using the selected region. Recipes are no longer mutated with a second sell-price field. The source catalog uses one recipe per line for reviewable diffs; shared metadata is formatted for editing, while delivery HTML is compacted by the builder.
