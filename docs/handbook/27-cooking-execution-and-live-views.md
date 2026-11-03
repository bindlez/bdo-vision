# 27 · Cooking execution, charts and live grind views

## Deep cooking plans

The exact linked [Organic Feed variant](https://bdolytics.com/en/crafting/54018:f9c0e088e9ca)
is recipe `recipe:54018:f9c0e088e9ca`, item 54018, in the shared catalog.
Cooking has 152 supported variants in this catalog. Tests also expand Kamasylvia
Meal to more than twenty stages, rather than proving only a single-level recipe.
Depth remains bounded at 12 and material traversal at 400 nodes. Limits and
unknown prices remain explicit; no infinite or guessed plan is presented as exact.

**Start next stage timer** chooses the first unchecked stage, uses its own saved
mastery/speed/yield model, and starts the existing planning timer. It never sends
game inputs. Its direct ingredient replacement-cost model is separate from whole
chain economics, so intermediate value is not sold/credited twice. Stage forecasts
disable blocked-capture extrapolation. Optional accepted crafting loot follows
the existing timer attachment contract, including one recording owner at a time.

The preparation checklist advances only on explicit user confirmation. Timer expiry
does not confirm output or start a consumer recipe. Verify actual quantities after
random yields, keep the surplus or repeat production as needed. A stage already
launched cannot launch again while a matching recipe timer is running; after all
matching timers finish or are cancelled, repeating the stage is allowed. A large
stage above the existing 256-tool-chunk bound asks for a smaller plan instead of
silently truncating the production requirement. Resetting a checklist does not
cancel independent timers; review them before beginning a replacement plan.

Unknown-method processing/exchange recipes are excluded from automatic make-all
choices. They may be selected manually, but the new stage launcher refuses to guess
an acquisition timer for them. Organic Feed therefore does not automatically turn
the zero-second Special Onion exchange into an invented cooking action.

**Lowest priced substitutions** traverses enabled branches, compares valid
substitution ratios using cached market/NPC purchase prices, and updates local
choices. It does not fetch or claim to solve a globally optimal make/buy network.
Traversal is limited to sixty unique recipes and depth twelve. Individual variant
and make/buy controls remain available for every exposed branch.

Three pie/donut views show stage seconds, priced cash-input values and expected
retained output values. Top categories are grouped into Other with legend values
and percentages. Unknown cash inputs are absent from the priced-input distribution
and keep cash totals unpriced. Kept outputs are excluded from the revenue pie;
enabled exchange value is included once. No chart changes accepted stock/silver.

Source ownership remains `crafting-studio.js/css` and `crafting-engine.js`. Build
the owned planner, CP block and demo as documented in chapter 26. The cooking
preview is generated with `scripts/build_crafting_demo.py --cooking`; it opens
Organic Feed with the chain expanded. Its dated price snapshot and simulated
elixir feed remain explicitly separate from actual game OCR. Use the live paired
planner for current regional quotes. No synthetic cooking loot is implied.

## Native session presentation

`grind_charts.py` owns event-driven Canvas donuts and the pure `personal_best`
comparison. Current runs need sixty observed seconds and complete item pricing;
eligible completed peers need ten observed minutes at the same spot/activity.
Peer accepted quantities are revalued at current prices. Frozen history valuations
remain intact. This comparison changes neither history nor silver totals.

Silver targets are optional, nonnegative and session-scoped in the additive
`grind_money_goals` table. A goal is an item-value target, before fees/costs. Partial
priced value stays labeled; unknown items do not become free or count as silver.
Item pursuits continue separately. Completed runs retain their saved target.

`live_grind.py` uses the existing one-second insights tick only when its native
window is visible or OBS sharing is explicitly enabled. The native window is
compact and always-on-top; borderless/windowed game mode is needed to see ordinary
desktop windows over the game. It is not a game injection or exclusive-fullscreen
overlay. Pause/finish buttons call the existing session controls.

## OBS setup and privacy

In Grind, enable **Share with OBS · local only**, then **Copy OBS URL** and paste
it into an OBS Browser Source. `/stream` serves a small transparent page;
`?clock=0&loot=0` hides those two widgets. This is a fixed layout with visibility
options, not a draggable layout editor. Turn off sharing to revoke data access.

`/stream-state` is opt-in, loopback-only and subject to the existing strict host/
origin checks. It exposes only the small current-run value/rate, coverage times,
goals and latest six accepted items. It is independently gated from planner loot
sharing and does not upload to a server. Request bodies cannot turn it on.

The browser reads every two seconds while visible, backs off when hidden, uses a
four-second request deadline and clears values on error/stale snapshots. No OCR
is performed by the overlay. The native publisher stays quiet when neither consumer
is enabled. Lite Use continues to stop extra OCR; enabled live views display its
paused capture state. No new packages or chart framework were introduced.

Tests cover exact linked/deep chains, stage launch and duplicate prevention,
escaped donut labels, native chart clearing, default-off publisher work, goal
persistence, same-price pacing, disabled stream rejection and cross-origin denial.
See [the explicit feature audit](../GARMOTH-APP-COMPARISON.md) for remaining gaps.
