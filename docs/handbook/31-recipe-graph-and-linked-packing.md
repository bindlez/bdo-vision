# Recipe graph and linked packing

## One catalog, two directions

Do not store recursive copies of recipes inside recipes. The source remains
[recipes.json](../../desktop/assets/recipes.json), with stable recipe variant IDs,
output item IDs and ingredient slots. [crafting-data.json](../../desktop/assets/crafting-data.json)
stores shared item names/weights, substitution groups and mastery metadata once.
An item may be produced by several recipe variants and consumed by many recipes.

The [engine](../../desktop/assets/crafting-engine.js) exposes three complementary
views of that data:

- `indexRecipes`: item-to-producing-variants lookup used by cost planning.
- `productionGraph`: selected recipe's complete upstream structure, regardless of
  the economic Make/Buy switches. Item nodes are `item:<id>`; recipe nodes use
  stable variant IDs. Input edges carry exact resolved whole-item ratios. Output
  and rareOutput edges carry configured expected yields, not verified counts.
- `downstream`: cached reverse ingredient index for continued production uses,
  including substitution group values and bounded future routes.

The graph keeps references to canonical recipe records. Chosen variants and
substitutions are scenario settings, not mutations of the catalog. Cycle guards,
12-level/60-recipe bounds and visible warnings prevent runaway traversal. Recipe
steps are appended after their prerequisites; branches state what they feed.
When a cycle/limit warning exists, the map is partial rather than a valid complete
execution order. Missing/unverified manual acquisition methods remain input leaves.

This is an in-memory, on-demand structure. No second database, serialized nested
recipe tree, package installation, background worker or network request is needed.

## Full line versus selected financial route

The compact line shows how all known selected subrecipes relate. The economic plan
may still buy intermediates. **Plan entire chain** explicitly changes that route
to Make intermediates; simply viewing or selecting a packing step does not.
The checklist/timers/real loot ledger remain separate.

Up to four recipe cards appear together. Larger chains show all step selectors
and the chosen packing card, avoiding dozens of simultaneously editable tables.
Each selector shows its max-load capacity and consuming recipe names. Every card
uses the same entered current/max/reserve LT; deposit/update between stages.
Independent max loads are not a balanced quantity plan for the entire chain.
Use the Production workshop's required stage batches for that plan.

**Full chain overview** is an optional alternative to the focused view. It renders
every bounded recipe packing card beside an expandable dependency tree, with a
four-part cost/net/time summary. Below 1,000 px, the tree moves below the cards.
The tree/totals are a view-only full-make preview for the final target and current
owned stock. They do not change the selected Make/Buy map or adopt all the packing
maxima as one production plan. **Plan entire chain** explicitly adopts Make.
The preview is computed only while overview is open; no background work is added.
Generate its independent Balenos Meal example with `build_crafting_demo.py --overview`.

## Linked quantities

`ingredientRatio(recipe, itemId, quantity, context)` resolves substitutions,
combines duplicate item IDs, then calculates:

```
batches = floor(entered ingredient quantity / resolved quantity per craft)
companion ingredient quantity = batches * its resolved quantity per craft
leftover = entered quantity - batches * anchor quantity per craft
```

Only whole items and at least one complete craft are accepted. For ratios 1:2:3,
entering 1,000 in the first field produces 1,000 / 2,000 / 3,000. Entering 14,000
in the second produces 7,000 / 14,000 / 21,000. An amount not divisible by the
anchor ratio leaves an explicitly shown remainder; the anchor snaps down on blur.
Companions update while typing, and focus stays with the edited field.

The root card updates the root batch target/economics. A subrecipe card updates
only that independent packing load, not the final product target. Per-recipe load
counts, focused step and leftover notes are stored with the existing Studio state.
Entered bag quantities stay separate from general owned stock.

`carry` also accepts `options.batches`. It returns both maximum capacity and a
`selected` load assessment using the same peak-LT formula as max packing. The UI
reports overflow, tool-use excess and a bounded weight meter. **Fill to max** uses
the calculated rounded maximum. A load timer cannot start for an overweight or
tool-limited selected load, even if invoked through an obsolete button reference.
Existing duplicate-timer and chunk-count guards remain.

## Tests and extension points

The pure and shipped-page regressions live in
[test_crafting_logistics.js](../../scripts/test_crafting_logistics.js) and
[test_crafting_page.js](../../scripts/test_crafting_page.js). They cover the 1:2:3
example, remainder handling, selected-load overflow, the exact Sungnyung ->
Nurungji -> Cooked Rice chain, unique nodes, edge quantities, cycles, a large meal
chain and actual bound ingredient inputs in the shipped HTML.

To add recipes, preserve unique variant IDs and numeric item IDs. Use existing
substitution groups instead of hardcoded special cases. Regenerate owned HTML and
all demos after changing UI/engine assets. The `--weight` preview is explicitly
synthetic and has separate storage. See [weight model](30-weight-and-production.md)
for assumptions and [build ownership](08-planner.md) for release instructions.
