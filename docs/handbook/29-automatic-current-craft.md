# 29 · Automatic current craft

## Player flow

With a verified cooking/alchemy utensil and recorded loot capture enabled, begin
crafting in BDO. Leave **Detect automatically** on in Craft. You do not select a
recipe, choose a Crafting session or manually enable Crafting mode for this view.
Two matching output captures identify the family; rare output can identify its
normal parent. This adds no separate OCR operation. Existing tool/loot capture
must still be readable; Lite Use intentionally stops loot OCR and inference.

The Current craft card appears above daily totals. Its measurements are:

| Metric | Meaning |
| --- | --- |
| Captured item value | Accepted related output quantities × current cached unit quotes |
| Captured value/hour | That value ÷ readable observed crafting seconds × 3,600; starts after sixty seconds |
| Projected value/hour | Expected normal/rare output value per action × 3,600 ÷ tracked seconds per durability use |
| Projected scanned-tool value | Expected value per action × durability verified at the scan, not maximum capacity |
| Remaining estimate | Expected value per action × the current estimated remaining durability |
| Modeled profit/hour range | Expected retained normal/rare value minus cheapest priced substitutions for priced valid variants, divided by modeled action time |

The full-tool projection assumes the same recipe continues for the scanned
durability. It is a baseline model, **not captured value plus a guaranteed future
payment**. Random extra alchemy drops and kept byproduct/CP value aren't forecast.
Actually captured related extras can contribute to captured item value. Unknown
quotes stay unpriced; a partial captured total says what is excluded. No sale is
confirmed. Recipe variants and actual consumed substitutions cannot be read from
the output alone, so ingredient profit is explicitly a model, not actual net cash.

Mastery uses the saved native Imperial profile for the craft type, with zero/base
mastery as the default assumption. No recipe entry is needed for quantities and
gross valuation. The secondary profit range assumes 84.5% sale retention; it is
shown in model details. Yield/pace assumptions need not match the player's actual
random run. Tool usage progress is an estimate. Milestones use captured units only.

Expand **Craft graphs & model details** for a bounded captured-value timeline,
priced-output donut, observed/excluded-time donut and forecast assumptions. The
optional manual budgets/linked recipe sessions remain accessible separately; they
are not a requirement for automatic recognition.

## Inference and uncertainty

`auto_craft.py` indexes cooking/alchemy recipe families by normal and rare output
names. It matches only the tracked utensil's craft type. At least two distinct
captures, separated by 0.5 seconds and no more than ninety seconds apart, must
agree. Two notifications in one captured frame are not independent witnesses.
Ambiguous output-to-family mappings remain unknown rather than selecting the first
recipe. A positional utensil must already have a verified accepted durability
reading; a manual timer without a verified tool cannot identify a craft.

Each confirmed tool session has an independent recipe run. A repeated new family
starts a new segment from the remaining durability estimate. Previous runs remain
saved. Replacing a tool resets the evidence. Restarted app state is retained for
inspection but cannot silently resume against a new unverified tool/session.
Only related accepted outputs are attributed; this is not a claim that every item
obtained while standing in a residence was crafted by the current recipe.

Observation uses the existing one-second tick and a monotonic clock. Both prior
and current capture states must be readable to credit an interval. Blocked, stale,
unreadable, stopped and Lite Use time is not credited. Long scheduling gaps are
conservatively bounded. No drops are invented during excluded intervals; the tool
countdown and its continuation assumption remain an independent estimate.

## Storage, views and sharing

`auto_craft_runs` stores a bounded run summary and at most 48 cumulative quantity
samples. `auto_craft_members` maps accepted loot IDs to inferred runs. Accepted
quantities and original ledger kinds are never rewritten. A SQL LEFT JOIN derives
Crafted/Rare craft labels for native views. Home and optional crafting-timer
earnings include those member IDs without requiring manual Crafting mode. Membership
never adds another loot row. The original ledger remains available for audit.

`auto_craft_ui.py` integrates the controller and native card. It uses existing
PriceBook lookup/cache APIs: one bounded exact-ID request on detection, then the
shared five-minute cache. It prioritizes normal/rare outputs and default ingredients,
with up to 64 IDs; unquoted alternatives remain unknown. Work is backgrounded;
Tk state is updated on the UI thread. A changed recipe is queued after an in-flight
request. No account data, captures or run contents are uploaded for market lookup.

No extra capture loop or new package exists. Lite Use does not repeatedly query
prices, save run snapshots or redraw automatic charts. Idle/retained state is not
repeatedly written when unchanged. Visible graphs are bounded and draw on demand.

The paired planner receives `crafting_loot.auto_craft` only through existing
optional sharing. Turning sharing off hides the card. `crafting-loot-view.js` renders
recipe/status text safely, displays the three automatic metrics and lazily draws
value graphs. It does not change the recipe the player is deliberately planning.
The offline demo generates explicitly synthetic elixir samples; after two sample
events it displays a simulated automatic card. It does not run native OCR.

## Regression coverage and limits

Pure tests cover two-capture evidence, duplicate IDs, same-frame rejection, wrong
utensil types, ambiguous mappings, rare-parent identification, kept byproducts,
unknown prices, capture gaps, recipe switches and retained restart state.
Native tests exercise membership without ledger mutation, Home/timer integration,
the card and charts with no manual recipe selection, saving and disabled/Lite Use.
Browser tests exercise metrics, paused state, safe text and lazy charts. The existing
recording-cache tests now wrap the derived history read so unchanged frames still
cause only one history load.

These are fixture and isolated integration checks. They do not establish a live
game recognition percentage or guarantee that OCR captured every output. The
existing loot/tool readers and their diagnostic images remain the evidence source.
