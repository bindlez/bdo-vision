# 22 Â· Crafting platform: recipes, prices, models and extensions

## Ownership and editing order

The production catalog is `desktop/assets/recipes.json`; shared metadata, groups,
mastery and optional alchemy-extra distribution data are in `crafting-data.json`.
`crafting-provenance.json` records dated public source response hashes. These are
factual normalized records, not copied reference-site calculator implementation.

| Owner | Responsibility |
| --- | --- |
| crafting-engine.js | Pure arithmetic, substitutions, recursion, queue stock, yields, costs, unknowns |
| crafting-studio.js | Saved models, main UI, production tree, graph disclosure, queue and timer/native handoffs |
| recipe-browser.js | Indexed search, methods, favorites, bounded pages and optional opportunity filters |
| crafting-loot-view.js | Region/ID quote join and accepted-loot presentation |
| vision-timers.js | Existing timer ownership, earnings boundaries and receipt handling |
| price_book.py | Shared SQLite quote cache, exact selected IDs and optional broad snapshot cache |
| recipe_market.py | Bounded streaming public market reader; no scheduler |
| craft_economy.py | Native model validation and observed-session cost model |
| build_crafting.py | Embed owned assets/catalog into the actual shipped inline planner |

After changing an owned asset, run `python scripts/build_crafting.py`. Rebuild CP
with `python scripts/build_cp.py`; rebuild the offline crafting preview with
`python scripts/build_crafting_demo.py`. The planner's legacy Research summary
delegates economics to the Studio engine. Do not restore a separate one-output
calculation or an item-price editor there.

## Recipe schema and stable identities

Each record has `id`, `recipeKey`, `itemId`, `name`, `type`, `method`, `mats`,
`minProc`, `maxProc`, `xp`, base seconds, and optional `rare`. An output name can
have several recipes; index by recipe key/ID and keep an array per output ID.

A material has a concrete default `itemId`/name/quantity. Group materials also
have `groupId`, required group units and replacement value. Resolved quantity is
`ceil(required / chosen value)` **per craft**, then multiplied by batches. The
selected concrete identity is what inventory, shopping, quote lookup and native
session linking must use. Group labels are not market item identities.

The importer preserves existing IDs by exact recipe key; legacy name IDs are used
only when migrating an older catalog without keys. Do not let a new API ordering
reassign an existing saved ID to a different variant. Feed public response snapshots
to `python scripts/import_crafting_data.py SNAPSHOT_DIRECTORY`. Review changes and
source hashes; never import from a player's profile or another site's private API.

## Expected outputs and timing

Mastery uses the last bracket not exceeding the supplied mastery. Normal cooking/
alchemy output starts at the midpoint of the recipe range and incorporates the
bracket's maximum-proc chance. Rare cooking/alchemy outputs use the documented
planning model; unknown processing rare chances contribute no invented output.
Mass timing and success assumptions are visible and editable. Processing base
seconds remain per recipe/method, not one accidental global value.

Minimum skill requirements are absent from this public response. Do not infer them
from recipe names or treat an expectation as a guaranteed low-level yield. Link game
details and retain model overrides. Alchemy extra-item valuation is optional and
uses normalized tier shares; incomplete prices leave expected profit unknown.

Intermediate rare substitution is opt-in on that intermediate recipe's model and
uses three normal-equivalent units per rare proc. It is an assumption the player
must verify for the ingredient. This equivalent surplus is not a literal inventory
count. Intermediate extras are not additionally sold or double-credited.

## Costs, stock and recursive accounting

`plan` never writes inventory or loot. It copies owned stock for a single plan, or
uses the queue's shared ephemeral stock. Original owned inputs retain economic value
even though they reduce shopping cash. Buy inputs use a market quote or a labeled
NPC purchase price when available. NPC selling quotes must not become buying prices.

Making an intermediate charges the full required whole batches. Produced excess is
tracked separately from original owned stock so its reuse is not charged again.
Queue order matters. Main and rare outputs kept by the user are excluded from sale
revenue. The tree is bounded at depth 12 and 400 material nodes; cycles fall back
to buy with a warning, while an exceeded limit makes the result incomplete.

Unknown input prices leave cost unknown. Unknown sell outputs leave revenue/profit
unknown, while known input cost and required quantities remain useful. Known partial
values are not displayed as complete totals. The sale helper applies bonuses to
the 65% collection base; effective retention can be entered directly.

Byproducts are kept by default. Optional material exchange value counts whole
10-item batches and is an alternative to CP, never additional CP income. Output
graphs describe expected production and value sensitivity. Recorded timer graphs
use accepted events; blocked-capture projections never enter either ledger.

## Market request contracts

`POST /craft-quotes` retains names compatibility and accepts exact `ids` (1â€“64)
plus NA/EU region. Selected plans use exact IDs and a five-minute cache. No catalog
download is needed for those lookups. Common NPC-only ingredients and imperial
outputs are excluded from unnecessary market requests. Zero stock is distinct from
an unknown quote. A base quote, last sale, available stock and fetched time are
separate fields.

`POST /craft-market` is an explicit optional opportunity scan. It streams the public
response in chunks, caps bytes, row size, row count and time, and retains only known
recipe IDs with exact names. Enhancement level zero is selected explicitly when
levels are supplied. The result is cached for 15 minutes. Daily average volume is
fourteen-day volume divided by fourteen, never today's observed sales. There is no
polling thread and no OCR work. Both routes use the existing loopback/origin guard.

## Native and timer integration

The browser sends `/craft-model` on deliberate model changes after its debounce,
with current instance ID, exact recipe, concrete material rows, region and a locked
recursive input cost per root batch. Native validation checks each material against
the source recipe/group and its required quantity; arbitrary ingredient identities
are rejected. An unpriced recursive cost stays unavailable instead of switching to
a different direct-input model.

Native Sessions store the exact variant ID. Older unique names remain supported;
ambiguous historical names stay unresolved. Finishing a session freezes the linked
model and matching-region quotes. No old session is rewritten. Input consumption
is still inferred from accepted main output divided by assumed yield; it is not an
inventory measurement. Rare-only or unobserved batches may be incomplete.

Browser timers lock costs, substitutions and region at start. Output prices use
current quotes; region mismatches keep modeled net unavailable. A projection is
optional, cooking/alchemy only, bound to a current connected blocked interval and
stopped at the timer end. Confirmed native tool holds, Lite Use, tray and existing
quest/loot readers are untouched by these calculator additions.

## Rendering, budgets and tests

The recipe browser renders at most 50 cards; its text search index is built once.
Profit/EXP ranking is explicit; ordinary alphabetical browsing does not value every
recipe. Details preserve disclosure state. Profit graphs build when opened. SVGs
are bounded; there is no animation loop, chart library, worker or new runtime package.

Run `node scripts/test_crafting.js` for catalog/model behavior and
`node scripts/test_crafting_page.js` for the shipped owned blocks' DOM fixture.
Run `python dev.py test crafting_catalog crafting_studio craft_economy recipe_market
cp cp_forecast` and then `python dev.py check`. The fixture is interaction coverage,
not a visual browser or live game check. Follow the package checks and history-safe
upgrade contract before installation.

The offline demo uses a dated compact market snapshot with simulated drops. Its
network policy blocks connections. It has separate storage keys and cannot see BDO.
The [reference matrix](../CRAFTING-REFERENCE-MATRIX.md) records supported capabilities
and known limits. The [project paper](../PROJECT-PAPER.md) explains the broader lessons.
# Imperial quick picks

The Imperial section has Cooking/Alchemy tabs and one mastery input, remembered
per life skill. Two recommendations highlight the highest modeled buy and craft
profit. One compact table compares costs and profit side by side; clicking either
profit header ranks descending, with unknowns last. It shows 20 rows initially,
with a Show all control. No grade, CP or quantity input is required. All tiers
are compared, so life-skill eligibility and remaining delivery allowance still
need checking in game. Stock warnings are explicit, not assumed availability.

The existing on-demand `/craft-market` snapshot supplies exact-ID quotes; no new
polling or OCR. Buy cost multiplies meal/elixir quantity by the quote. Craft cost
buys inputs, chooses cheapest priced substitutions and rounds expected batches
up. Rare-output recipes use their rare yield. Surplus and side outputs receive
no cost credit. Delivery uses the existing imperial payout/mastery model without
market-sale tax. Costs link to the corresponding recipe. `imperialRanks` owns
calculations; `craftImperialRender` owns rendering. Run `node scripts/test_imperial.js`
and `node scripts/test_crafting_page.js` to verify math and shipped controls.

### Stock, daily totals and advanced analysis

Total CP is optional and remembered in the existing Studio state. When supplied,
the comparison models `floor(CP / 2)` boxes, amortizes whole-batch crafting cost
over that allowance, and shows both per-box and potential daily profit. It assumes
the entire allowance is unused and never writes forecasts into recorded history.
The two additional in-stock recommendations require enough known market stock
for that full run. Unknown/zero/insufficient stock is excluded. Cooking/alchemy
recipe variants and group substitutions are reconsidered for availability; an
NPC input is allowed at its labeled purchase price. Input requirements aggregate
by item ID before checking stock. NPC fallback can cost more than an unavailable
market quote. Stock remains a snapshot, not a reservation. Missing stock is not zero.

The table includes both items per box and Imperial payout per box. Advanced graphs
are built only when their disclosure is opened. They show bounded top-six expected
buy/craft profits with a zero baseline, plus recommendation breakdowns of ingredient
quantity, cost, available stock, expected surplus and return on input cost.


## Inventory preview and tool capacity

Craft from inventory uses saved quantities for the selected recipe and its
ingredient substitutions. Paste a tab-separated item name and quantity on
each line to update multiple counts together. The slider shows modeled time
and Life EXP through the last batch covered by entered stock. Applying the
slider updates the plan amount. The planner cannot read complete item stacks
from the game. Update the entered inventory when stock changes.

A fresh recipe timer uses the selected full-tool capacity from 3,000 to 5,000
uses. Each timer card covers one chunk. Its queued remainder carries forward
with the selected capacity for later tools. The user replaces the tool in
game. A linked or manually entered durability timer follows the actual
remaining uses, which can be below 3,000.
