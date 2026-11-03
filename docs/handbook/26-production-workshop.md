# 26 · Multilevel cooking and alchemy workshop

## Player workflow

Open Crafting, choose Cooking or Alchemy, and select a real recipe. Set batches
or desired main output, mastery, speed, tax and owned ingredients. The existing
planner retains normal/rare yield settings, ingredient substitutions, expenses,
byproduct choices, processing recipes, Imperial comparisons, queues and timer links.

The **Production workshop** adds an explicit end-to-end preparation route:

1. **Make all intermediates** expands supported subrecipes recursively, using each
   selected variant and its own saved character/mastery model.
2. **Buy ingredients** clears make decisions along the selected recipe chain.
3. Expand intermediate choices to change make/buy and variants at deeper levels.
   Making a branch exposes its own ingredients and editable children.
4. Compare cash required, economic input value, total production time and expected
   profit with the buy-ingredient route. Owned inputs have economic value even when
   no new cash purchase is needed. Making all intermediates is not an optimizer.
5. Gather the existing shopping list. Work through ordered stage cards: input per
   batch, total stage inputs, crafting actions, expected yield, time and surplus.
6. Check completed preparation stages manually. This is a checklist, not evidence
   of crafting or a way to add items/silver to the ledger. The existing timer remains
   independently controlled. A complete checklist does not complete a game action.
7. Export the full runbook for shopping, ordered batches, inputs and warnings.

Unknown prices preserve quantities but block affected totals. Expected fractional
yield is not a guaranteed inventory count. When an intermediate's advanced model
enables rare-for-normal substitution, its expected output represents equivalent
normal units; the player must verify that replacement is valid in game.

## Calculation and ownership

`crafting-engine.js` remains the bounded, side-effect-free planning engine. Its
existing recursive `consume` walks dependencies, consumes inventory once, reuses
produced surplus and guards cycles/depth. Stage records now expose item identity,
type, inputs, quantities, expected equivalent yield and retained surplus. Children
are appended before consumers. Repeated subrecipe stages are preserved in order;
they aren't merged in a way that could hide a dependency or duplicate surplus.

`crafting-studio.js` owns rendering and actions. `craftStudioChainRoute` marks a
bounded recipe traversal (400 nodes, depth 12), not a background search or automatic
market optimizer. `craftStudioWorkshop` compares the same plan engine with `make:{}`
against current choices, using copied inventory. No second recipe database exists.

Checklist state is one active production plan in existing local planner storage.
Its signature includes recipe, root count, stage IDs, stage batches, outputs and
input identities/quantities. A changed requirement resets completion. Only a
consecutive prefix can be checked; unchecking a prerequisite clears later checks.
Price changes alone do not erase a preparation checklist. No completed checkbox
alters owned quantities, accepted loot, session totals or timer state.

The stage timeline uses proportional expected production seconds with exact text
values in the cards. Purchase bars show only the top eight priced cash inputs;
missing prices are explicitly excluded and cash totals stay unknown. These views
are HTML/CSS, with no chart library, animation loop, OCR scan or polling added.

## Verification and scope

The shipped-page test exercises real Balenos Meal and Elixir of Demihuman Hunt
chains, ordered stages, metadata, checklist progression/reset, runbook export and
returning to a one-stage buy route. Existing tests cover economics, substitution
ratios, inventory sharing, cycles, taxes, price gaps and escaped text.

Build owned assets with `scripts/build_crafting.py`, then `scripts/build_cp.py`,
then `scripts/build_crafting_demo.py`. Do not hand-edit generated planner HTML.
Run `node scripts/test_crafting.js` and `node scripts/test_crafting_page.js`, then
the full developer checks before packaging.

Reference comparison: [BDolytics crafting](https://bdolytics.com/en/crafting?category=alchemy).
Its dynamic page could not be exhaustively inspected in this change. This is an
independently implemented workflow; exact parity with every competitor option is
not a verified claim. OCR decisions were not modified here. Passing reader tests
prevents known regressions; it does not establish live game accuracy or zero misses.
