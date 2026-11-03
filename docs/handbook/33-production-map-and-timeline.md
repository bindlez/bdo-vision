# Production map, timeline and canonical recipe relationships

## Main planner workflow

The Recipe planner now opens with a connected map and timeline. Packing and the
previous calculation tools remain in the **Packing, recipe settings & detailed
calculations** disclosure underneath. Imperial and the stock-limited simulator
remain separate workspaces.

1. Find/select the product you are working on, or use Open detected product’s
   production map on the automatic current-craft card. That button reuses the last
   inferred family and existing catalog index; it adds no OCR. This is a planner selection, not a
   claim that the game is currently producing it. The source selector also retains
   the existing tool durability timer.
2. Pick **Finish as**, or choose one of the visible direct consumer chips.
3. Set the final batch target. A future product's target does not overwrite the
   selected ingredient's existing packing amount.
4. Inspect the entire required recipe graph. Violet marks the selected product;
   teal marks its route to the goal; the other branches are also needed. Toggle
   purchased/raw inputs or choose readable-size versus fit-to-screen display.
5. Select a recipe node or a numbered timeline row. Its inputs, full stage quantity,
   duration and consuming recipes appear alongside the map.
6. Start that stage's existing planning timer only when ready. No game action or
   automatic stage completion occurs. The separate Timers workspace opens.

The timeline is a sequential, prerequisite-first plan. Stage start/end offsets are
relative estimated production time, not wall-clock forecasts or observed progress.
Owned intermediate stock can remove a craft from the schedule. Travel, storage
trips and unverified manual acquisition durations are excluded. Use packing cards
to split stages into practical character-LT loads.

**Refresh whole-line prices** explicitly collects exact IDs from the entire chosen
route, including its forced substitutions. It reuses the protected Windows quote
endpoint, 64-ID request batches, bounded 256-ID set and existing five-minute cache.
There is no ongoing price loop. Responses for an abandoned goal or region cannot
replace the current view. Failed/offline requests leave the pending cache clean so
connecting the app and retrying works. Unknown prices stay unvalued.

## Actual recipe connections

The shipped catalog connects Fruit Wine (item 9201) to Serendia Meal, Knight Combat
Rations, Margoria Seafood Meal and Kamasylvia Meal, plus an Imperial box recipe.
It does not connect Fruit Wine to Balenos Meal. Balenos uses Beer, Cheese Gratin,
Stir-Fried Vegetables, Meat Croquette and Smoked Fish Steak. The UI only offers
reachable future goals and keeps Imperial delivery calculations in their workspace.

These are assertions about this versioned catalog, not a live-game accuracy claim.
When upstream data changes, update canonical data and rerun relationship tests.

## Run stopping rules

Cooking and alchemy each save their own default in the roadmap preferences. Both
start with **Tool durability**. Either can switch to **Ingredient stock**,
**Hybrid / whichever runs out first**, or **Manual final target**. Processing
defaults to a manual target and can use stock, without unrelated tool options.
LT remains a packing constraint, not an assumed run stopping condition.

Tool mode derives remaining uses from the existing synced reading and its cadence:
`max(0, last current - floor(elapsed seconds / seconds per use))`. The source is
labeled a countdown estimate, never a fresh OCR read. No new scan or poll is added.
The reader must have a valid sent signal, bounded count/cadence and plausible
timestamp; the bridge's initial placeholder is not a reading. An explicitly
entered fallback is labeled entered, not live. Old recipe inference is not used
to guess a tool's type. A provided explicit tool kind must match the recipe kind.

The existing bridge poll copies a few scalar fields and updates only the small
counter. The map replans on first usable synchronization/new tool session, edited
settings, Apply latest limits or an explicit start. It does not replan each tick.
Lite Use's initial scan and existing countdown therefore remain sufficient.

Ingredient mode uses exact resolved per-craft quantities and the independently
entered inventory available for this run. Duplicate input IDs are combined before
dividing stock. Missing is unknown; entered zero is empty. The packing bag counts
can be copied explicitly. There is no inventory OCR or invented stock, and storage
totals are not silently treated as carried quantities. Entered stock is merged by
maximum, not added again to an existing owned-stock total in the preview.

Hybrid requires both a usable tool value and every required ingredient quantity,
then takes the smaller craft count. Tool-only assumes adequate ingredients;
ingredient-only intentionally does not cap at tool uses. Zero schedules no crafts.
An unknown limit leaves the structure visible without a made-up timeline.

For a future goal, the selected product is first planned for its complete limited
run. Kept expected main output funds the future recipe through one shared stock
pool; missing companions can still require buying/making. Surplus is retained,
not sold twice. The selected product's prerequisite branch leads the timeline.
Random yields remain estimates. Starting another non-manual cooking/alchemy stage
first makes it the current craft, so its own rule can be reviewed before launch.
Only an explicit stage start creates a recipe timer; existing Tool Watch countdowns
remain distinct. Advanced packing/workshop timers remain explicitly labeled manual-quantity overrides. Stopping rules are planning/timer settings, not gameplay controls.

`test_run_limits.js` and the shipped UI checks cover defaults, independent saved
preferences, stock/tool minima, zero/unknown guards, synchronized countdowns and
full-run timeline quantities. The roadmap demo explicitly uses an entered example of 1,000 tool uses and stock
for 600 crafts so the tool/ingredient/hybrid difference can be tested without a game.
Other planning demos may explicitly select manual targets. None imply live OCR.

## Canonical architecture

[recipe-network.js](../../desktop/assets/recipe-network.js) is the shared data
layer. Each catalog/spec object pair gets one cached index:

| Index | Meaning |
| --- | --- |
| `byRecipe` | Stable recipe variant ID to canonical recipe record |
| `byItem` | Main output item ID to producing variants; backward-compatible planner index |
| `byName` | Legacy normalized-name fallback for existing financial inventory adapters |
| `producers` | Item ID to main/rare-producing recipe references |
| `consumers` | Item ID to consuming recipes and exact input slots/group conversions |

Recipe and item records remain in `recipes.json` and `crafting-data.json`. Do not
duplicate nested recipe objects or create a graph database. Relationship records
refer to exact IDs and canonical recipe objects. Groups expose every valid option
and its whole-item conversion; they do not assume all alternatives are simultaneously
needed. Output kind distinguishes a main product from a rare proc.

Caches are WeakMaps keyed by both immutable recipe array and immutable data-spec
object. Different substitution specifications cannot silently reuse the wrong
reverse index. The real planner shares its existing index with the same spec.
Treat all returned indexes as read-only; replace catalog/spec objects after edits.

`VisionRecipes.uses` answers both how an item is made and which recipes consume it.
`targets` performs bounded breadth-first traversal of future products, returning
one valid shortest path per recipe, input-slot choices and per-craft requirements.
Repeated outputs and recipe cycles cannot cause infinite traversal. The UI uses
eight future levels and at most 120 results; truncation is explicit. No missing path
is invented. Imperial/manual targets are excluded from production-timer navigation.

## From relationship path to an executable plan

[production-roadmap.js](../../desktop/assets/production-roadmap.js) merges a chosen
future path's input-slot choices and variant IDs into a copied planning context.
The selected product's actual variant is retained. This matters when an item is
an alternative in a substitution group: the preview must really use that item,
rather than showing an unrelated default substitution.

The existing engine builds the complete upstream graph for the goal, constructs a
local full-make map and allocates owned stock once. Only the goal's final outputs
receive final-output sale treatment; intermediates are consumed by later recipes.
Previewing a goal or focusing a node does not mutate the saved Make/Buy map,
inventory, packing amounts, queue, native profile or accepted loot.

`VisionRecipes.timeline(graph, plan)` aggregates repeated makes of the same recipe
variant, follows the graph's prerequisite order, and assigns cumulative offsets.
Inputs retain item IDs and quantities; durations sum to the existing plan's total.
A partial/cyclic graph or planner limit is exposed and blocks starting its stages.

Stage timer launch validates known methods, existing chunk-count limits and running
duplicates. Its model is a direct-input snapshot for that exact stage, including
the route's substitutions. A timer is not started when selecting a node. Native
tool timers and OCR scheduling are not changed.

## UI state and exports

The map uses its own `vision.craft.roadmap.v1` preference key for goals, focus and
display options. Only explicit selection of a different product or opening a
stage's packing view navigates the original planner. The stock-only Chain simulator
retains its own state and calculation contract.

Map focus/fit interactions reuse the current calculated view model. Recipe/goal/
quantity/model changes rebuild it on demand. There is no new polling, OCR capture,
graphics library, remote font, graph service or background timer. SVG nodes and
arrows are generated locally; names/IDs are escaped before rendering.

**Export map & timeline** creates `bdo-vision/production-plan-v1`: source and goal
recipe IDs, target, route choices/variants, stages, quantities, relative times and
warnings. It is marked estimated. It does not export a native account profile or
turn planned quantities into accepted loot. The same canonical IDs are suitable
for a later backend; backend persistence is not required for this local feature.

## Tests and editable files

- [test_recipe_network.js](../../scripts/test_recipe_network.js): all 990 recipe
  variants reverse-linked, main/rare identities, spec-specific group caches,
  Fruit Wine/Balenos facts, cycle bounds and timeline duration/order.
- [test_crafting_page.js](../../scripts/test_crafting_page.js): shipped map/goal
  controls, node focus, quantity isolation, export and stage timer duplicate guards.
- [build_crafting.py](../../scripts/build_crafting.py): loads `recipe-network.js`
  before the engine and embeds the roadmap after the existing Studio modules.
- [build_crafting_demo.py](../../scripts/build_crafting_demo.py): the independent
  `--roadmap` preview opens Fruit Wine and a valid future-meal goal.

Run `python dev.py check`, regenerate every relevant demo, then package a new
version. Keep source-ID data, expected planning quantities and observed loot as
three separate concepts throughout later extensions.


In rc.27 the map remains directly reachable through Map & timeline, alongside the visible crafting desk. Packing and calculations are no longer hidden behind the outer disclosure; the recipe list stays visible by default. See [the updated layout contract](34-overlays-and-crafting-desk.md).
