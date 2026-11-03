# Starting-stock simulator and Crafting workspaces

## Four separate workflows

Crafting has four local workspaces: Recipe planner, Chain simulator, Imperial
turn-ins, and Timers & completions. Switching hides other workspace panels rather
than destroying their state. The existing timer engine continues to run; its
existing refresh updates the small timer count. No new poll loop is added.
Recorded Vision output remains available in Planner and Timers, and is hidden
alongside the other unrelated content in Imperial/Simulator. Imperial cost links
explicitly return to the Recipe planner to inspect the selected recipe.

The layout is defined in [the shipped planner](../../bdo-market-intelligence.html).
[crafting-simulator.js](../../desktop/assets/crafting-simulator.js) owns switching
and the scenario UI. [build_crafting.py](../../scripts/build_crafting.py) embeds its
owned block. Do not edit that generated inline JavaScript separately.

## Scenario isolation

The simulator stores only its own scenario in `vision.craft.simulator.v1`. The
workspace preference is `vision.craft.workspace.v1`. It reads canonical recipe
data and current saved mastery/substitution/variant models, but never changes
Studio packing amounts, inventory, make/buy settings, queue entries, selected
recipe, timers, native profiles or accepted loot. Its result is in memory; exports
are explicitly marked simulations. Demos replace these keys with their own names.

Choose a final product, an ingredient anywhere upstream, and its total available
quantity. A ready-made intermediate is a valid starting point. Add any other
scenario stock separately; regular planner inventory is not silently imported.
Imperial delivery targets belong in the Imperial workspace; targets with no
verified processing method are excluded rather than assigned a guessed duration.

- **Buy missing companions:** maximize final modeled batches while never buying
  or manufacturing more of the starting ingredient. Other missing inputs may be
  acquired; quantities, cost basis and unknown prices remain explicit.
- **Use only entered stock:** every purchase is forbidden. Shared branches use a
  single stock/surplus pool, so one item cannot fund two branches twice.

The UI computes only on Simulate. Editing a field invalidates the old result and
disables export until recalculation. Graphs render on disclosure. Search limits
the recipe selector to 120 matching variants, with the selected recipe retained.

## Calculation contract

`VisionCraft.simulateProduction(recipe, options, context)` in
[crafting-engine.js](../../desktop/assets/crafting-engine.js) constructs a bounded
upstream graph, stopping at the starting item. Unneeded recipes before that point
are excluded. Cycles/limits in the remaining required route block simulation.

Scenario stock uses exact item IDs. The existing planning engine uses normalized
names internally; the adapter checks for ambiguous duplicate names and rejects
them instead of merging two IDs. It copies stock, strips any shared inventory or
produced pools supplied in context, and builds its own Make map. The starting item
is always a stock leaf. Other known intermediates may be made.

For a candidate final batch count, the existing recursive planner allocates stock
once and produces expected-yield intermediate batches, retaining surplus. A
candidate is feasible if it has no forbidden purchases: the source item in
companion-buy mode, or any item in stock-only mode. Exponential bracketing followed
by integer binary search finds the largest feasible count, capped at one billion.
At most 70 bounded planner evaluations are needed. The next count exposes the
shortfalls for one additional final craft. Zero feasible crafts is a real empty
result; it is not clamped to one.

Outputs include final main/rare products and modeled byproducts, plus intermediate
side rares/byproducts that have not been used as normal equivalents. The UI
aggregates matching output IDs. Main intermediate surplus stays in scenario stock.
Random alchemy extra-item distributions are excluded. This is a yield model, not a
guarantee that a real run will produce the expected quantity.

Economic input cost values owned stock at replacement cost. Cash describes only
missing companion purchases. Potential sale value covers final main/rare goods
after configured deductions; kept side outputs and surplus receive no silver
credit in that comparison. Unknown prices never block quantity simulation, but
unknown totals remain unvalued. No output is recorded as a sale or loot event.

The simulator does not model one continuously carried bag, bank/travel time,
inventory slot limits, price movement, market reservations or actual random streaks.
Use the separate packing cards for character LT. No stage starts in game.

## Validation and preview

[test_crafting_simulator.js](../../scripts/test_crafting_simulator.js) covers raw
and intermediate starts, fixed source supply, stock-only limits, shared branches,
leftovers, cycles before/after the starting point, missing prices, bounds and
planner/shared-pool isolation. [test_crafting_page.js](../../scripts/test_crafting_page.js)
executes the actual shipped scenario controls, lazy graphs, invalidation, export,
workspace visibility, timer count and preservation of original planner state.

Generate the standalone preview with
`python scripts/build_crafting_demo.py --simulation`. It starts from sample
14,000 Cooked Rice for Sungnyung, using labeled offline example prices. It cannot
read the game or change a real profile. Run `python dev.py check` before packaging.
