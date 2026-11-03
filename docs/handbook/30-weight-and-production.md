# Weight packing and forward production

The Crafting Studio answers two separate questions: how much can one ingredient
load hold, and what could the resulting product be used for next? These are
planning calculations. They do not withdraw items, read character weight, add
loot, change real inventory or control BDO.

## Player workflow

1. Select the exact cooking, alchemy or processing recipe and substitutions.
2. In **What should I grab?**, enter character maximum LT and current total LT.
   Current LT must already include equipment and all items currently carried.
3. Leave a reserve. If relevant ingredients are already carried, enter their
   counts in the packing table. Storage stock is deliberately separate.
4. Read the exact **Grab from storage** column. **Use this load** applies the
   modeled maximum to the recipe's batch target; exporting makes a text checklist.
5. **Rank cooking by longest load** compares the category using these same LT
   assumptions. Other sorts find most crafts/load or lightest inputs/craft.
6. Under weight settings, choose an output allowance, tool-use cap and optional
   rounding increment. Per-stage packing cards appear for intermediate recipes
   when Make intermediates is enabled. Each card has its own planner timer.
7. Under **Where can this product go next?**, inspect consuming recipes up to four
   stages forward. Queueing a route keeps intermediate output for later stages.

Deposit products and update current LT between packing stages. Each stage card is
an independent load using the same entered baseline; it does not simulate one bag
through a whole chain. Timers remain reminders and never start game crafting.

## Carry model and boundaries

Implementation: [crafting-engine.js](../../desktop/assets/crafting-engine.js),
`VisionCraft.carry(recipe, options, context)`.

For `B` whole crafts and ingredient `i`, define:

```
I = sum(quantity_i * unitWeight_i)
extra_i(B) = max(0, B * quantity_i - alreadyCarried_i)
load(B) = sum(extra_i(B) * unitWeight_i)
initial(B) = currentLT + load(B)
final(B) = initial(B) + B * (modeledOutputLTPerCraft - I)
peak(B) = max(initial(B), final(B))
usableLT = max(0, maximumLT - reserveLT)
```

An integer binary search finds the greatest `B` with peak <= usableLT and within
the optional tool-use cap. A rounding increment reduces that result; it never
rounds above capacity. Duplicate input IDs are combined before bag stock is
subtracted. Bag ingredient weight cannot exceed total entered current LT.

**Ingredients only** constrains initial weight and ignores accumulating outputs.
**Expected outputs** includes configured normal and rare yields plus configured
byproduct rates. **Normal + rare maximum procs** uses recipe maximum normal/rare
procs. Neither output mode guarantees a bound on all random extras, especially
alchemy side products. Keep reserve space; slots, nonstacking behavior and in-game
rules can stop a run earlier. Acquisition/manual exchange time may be unknown.
The model does not assume a character's overload allowance beyond entered LT.

Missing required weights return an unavailable result, not zero weight. Legitimate
zero weights remain zero. Invalid/blank LT is rejected. Numeric inputs and search
are bounded; no-cap zero-weight cases are marked as reaching the planner cap.
Only finite usable results can be applied to a production target.

Time per load equals batches times saved seconds per batch. It does not include
bank visits or unknown acquisition time. Each recipe uses its own saved mastery,
yield and speed settings. A longest-load ranking is not a profit ranking.

## Forward graph and queue accounting

`VisionCraft.downstream` uses an item-ID reverse ingredient index, including
substitution groups and their conversion values. The immutable recipe catalog's
index is cached in a WeakMap. Traversal is bounded to four levels and 60 nodes;
paths cannot revisit an output item. Each consumer needs whole batches and may
require additional ingredients. A missing consumer means absent from this catalog,
not proof of no in-game use. Rare root output can be selected separately.

An overridden product quantity is a what-if preview. To queue its route, the root
target's expected quantity must match. This prevents invented starting stock.
Queue entries force the chosen actual upstream ingredient in substitution slots.

`VisionCraft.productionQueue` plans in visible order against one copied inventory
and produced-output pool. Kept main/rare output is eligible for later inputs;
expected fractional units are rounded down before allocation. Future stages cannot
fund earlier ones. Consumed produced stock is not charged again, and kept output
does not also receive sale revenue. Reordering recalculates balances. Remaining
planning stock is shown separately from verified game inventory. Actual yield must
be checked before executing the next stage. Existing accepted loot is untouched.

## Ownership, validation and efficiency

- UI: [crafting-studio.js](../../desktop/assets/crafting-studio.js).
- Category sorting and bounded recipe cards: [recipe-browser.js](../../desktop/assets/recipe-browser.js).
- Carry and queue regressions: [test_crafting_logistics.js](../../scripts/test_crafting_logistics.js).
- Shipped-HTML UI regressions: [test_crafting_page.js](../../scripts/test_crafting_page.js).
- Offline example: [build_crafting_demo.py](../../scripts/build_crafting_demo.py), `--weight`.

Regenerate owned HTML with `scripts/build_crafting.py`, then regenerate demos.
Use `python dev.py check` for all checks. No new runtime package, OCR call, market
poll or background timer is needed for packing/ranking. Capacity uses a bounded
integer search; category rankings calculate on demand and render at most 50 cards.
The measured pure cooking-catalog calculation is a small local benchmark, not an
FPS or OCR-accuracy claim.

The reference Weight tab was inspected at
[BDolytics Nurungji](https://bdolytics.com/en/crafting/820831:8dd94cf6d723).
Our tests use an explicit example of 2,700 LT, zero current/reserve LT and
ingredients-only rounding to 100: Cooked Rice 5,100 batches and Nurungji 24,500.
These are test assumptions, not a claim about the reference site's configured
character weight. The standalone weight demo labels its sample character values.
