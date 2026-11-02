# 21 · CP Intelligence and byproduct decisions

## Deep payoff model · current extension

The native tab now has Decision, Payback, Milestones and Model pages. The browser keeps the payoff answer and signed recovery graph visible; detailed forecasts, target solvers, stress tables, optimizer and simulated achievement ladder are expandable. Opening Full Planner explicitly transfers the calculated native inputs through the same-origin read-only `/cp-plan` endpoint. Browser edits remain local and do not silently change the native scenario.

New pure arithmetic lives in [cp_forecast.py](../../desktop/cp_forecast.py), mirrored by [cp-engine.js](../../desktop/assets/cp-engine.js); [cp-analysis.js](../../desktop/assets/cp-analysis.js) owns the detailed browser markup and static recovery chart. [Forecast tests](../../tests/test_cp_forecast.py) cover exact integrals/inverses, costs, deployment caps, reserves, milestones and randomized advanced native/browser parity. Rebuild with `python scripts/build_cp.py` after changes. Do not edit only the generated inline HTML.

For a time `t`, setup delay `d` and ramp duration `r`, let `a = max(0, t-d)`. Effective full-income days `P(t)` equal `a` if `r=0`, `a²/(2r)` if `0<a<r`, and `a-r/2` after the ramp. Uptime multiplies steady daily income by its percentage. Additional earnings are `daily × P(t)`. Setup costs apply once when a route gains new whole CP; the cash route has none. Investment is foregone selected cash plus setup cost. Retained cash may be negative, meaning additional funding is required.

To solve payback, set `q = investment / daily`. With a positive ramp, recovery inside it takes `sqrt(2*r*q)` productive calendar days when `q <= r/2`; otherwise it takes `q+r/2`. Add the setup delay. Zero income with a positive investment has no payback, not zero days. Forecast displays suppress false precision beyond ten years. Required-income solvers reverse the same integral, including uptime, and reject a deadline that occurs entirely during setup.

Income basis can be per new deployed CP, or a whole-project amount for the all-CP route. Whole-project daily income scales by `route deployed CP / all-CP deployed CP`, then by uptime. This assumes equal marginal income for the modeled deployment; it does not infer real node or worker profits. Income defaults to zero. Cautious/base/strong cases use 50%/100%/150% of the entered income. The nine-cell sensitivity table separately scales foregone cash by 80%/100%/120%, leaving setup cost fixed; it is not a substitute for market quotes or a probability forecast.

The target optimizer evaluates at most 600 whole-CP targets, including cashing out, and uses minimum complete batches to attain each. It filters on retained cash reserve and maximizes cash plus modeled incremental income at the chosen horizon, preferring fewer batches on ties. It never loops over millions of individual byproducts. CP advancement uses an immutable 601-entry EXP prefix table and binary search; target EXP lookup is constant-time. Existing four route cards remain the named routes; the optimizer is a separate explicitly modeled suggestion. Its result is conditional on available prices and the equal-income assumption.

Recovery checkpoints at 10%, 25%, 50% and 100% are **simulation milestones**, not actual achievements or tracked earnings. The simulation slider updates only its small DOM section; it does not rerun the optimizer, replace the focused slider or collapse open details. No elapsed-time timer, animation loop, game capture, network polling or ledger write is added by CP analysis. The optional grinding-rate input merely converts opportunity cost into equivalent hours at an entered rate.

The original simple no-ramp/no-setup equations below are the special case with 100% uptime, zero ramp and zero setup cost. Use the current integral above whenever those assumptions change.

The native **CP Info** tab and paired planner **CP Intelligence** page compare NPC sales, priced material exchanges, CP turn-ins and split allocations. The standalone [interactive preview](../../demo/bdo-vision-cp-demo.html) works offline with the user's hypothetical 750,000-catalyst example. It has no live market connection or screen access. First-use example inputs are explicitly labeled; they are not detected inventory.

## Ownership and editing map

| File | Responsibility |
| --- | --- |
| [cp-data.json](../../desktop/assets/cp-data.json) | Small factual CP bracket table, three byproducts, batch sizes, exchange rewards, vendor values and dated source links. |
| [cp_planner.py](../../desktop/cp_planner.py) | Native pure arithmetic, validation, batch accounting, allocations and modeled income. No disk writes, captures or network requests. |
| [cp-engine.js](../../desktop/assets/cp-engine.js) | Equivalent pure browser engine. Randomized parity tests compare native and browser calculations. |
| [cp_ui.py](../../desktop/cp_ui.py) | Native inputs, saved local scenario, event-driven graph, explicit market refresh and optional CP snapshot. |
| [cp_reader.py](../../desktop/cp_reader.py) | Small default-HUD crop, two bounded passes, strict total/unused/progress parsing and exact agreement. |
| [cp-planner.js](../../desktop/assets/cp-planner.js) / [CSS](../../desktop/assets/cp-planner.css) | Full web planner, allocations, sources, formulas, accessible SVG graphs and explicit reader controls. |
| [build_cp.py](../../scripts/build_cp.py) | Embeds owned assets between `VISION CP` markers in the shipped planner and generates the standalone demo. |
| [test_cp.py](../../tests/test_cp.py) / [test_cp.js](../../scripts/test_cp.js) | Numerical examples, boundaries, tax, unknown quotes, leftovers, deployment delay, input rejection and OCR behavior. |

After an asset edit run `python scripts/build_cp.py`. The marker block is generated; editing only the asset without rebuilding does not change the shipped page. Run `python dev.py test cp bridge`, then `python dev.py check`.

## CP data provenance and limits

The September 2025 game changes reduced the old CP EXP requirements. Do not reuse pre-change tables. The current factual `byproductsPerLevel` data was checked against BDolytics' public calculator procedure on November 2, 2026. Multiply by 90 EXP per 10-item byproduct and round to the nearest integer EXP, for current CP 0 through 599. Every bracket's reconstruction error was less than 0.5 EXP. Do **not** subtract its accumulated float32 `byproductsTotal` values: that loses precision. Store a compressed 24-bracket integer table instead of retaining 651 repetitive rows or proprietary calculator source.

`curve` entries are **current** CP → EXP needed for the next CP. Current 475–499 costs 414,778 EXP per point. Current 500–524 costs 571,594; 525–549 costs 914,550; 550–574 costs 1,463,280; 575–599 costs 2,341,248. The model stops at 600: it reports residual unmodeled EXP and does not invent CP beyond the verified range. This is a model limit, not a claim of an absolute game cap.

Game-displayed starting percentages are rounded. Projected ending percentages and exact target requirements inherit that small uncertainty. No CP EXP buffs or rounding policy beyond the supplied percentage are assumed. Recheck the source table after a game balance patch, update the checked date and rerun the numerical regressions. Never fetch a curve automatically on startup.

Exchange facts were cross-checked with current item records and the user's cooking/farming tooltips. Mysterious Catalyst and Witch's Delicacy exchange 10 items for 900 CP EXP; Blush Leaf exchanges 20. All three have a 20,000-silver NPC sale baseline. These are mutually exclusive turn-in choices. Alchemy/cooking/farming EXP is an additional benefit without an invented silver value.

## Arithmetic contract

`available EXP = Σ floor(stock / batch size) × 900`. Carry starting EXP through each CP cost in order. Never divide all gained EXP by the starting CP cost. `target batches = ceil(EXP still needed / 900)`. Do not consume a fractional batch. Leftover items stay in inventory under the default material-exchange policy. NPC selling is optional.

The default cash policy is the highest **priced material exchange**, using exact reward IDs from the existing market system. A material exchange uses `reward units × market unit price × sale retention`. Leftover byproducts stay in inventory. Direct NPC sale is an optional browser alternative; the internal legacy `best` policy remains only for backward compatibility and regression comparisons. Saved browser `best` settings migrate to `market`.

Missing prices are not zero. If an owned byproduct with whole batches has no priced material reward, `cashComplete` is false, cash/payoff fields are null and silver graphs remain unavailable. CP EXP and projected CP still work. If some alternatives are unpriced but one reward is priced, the result is explicitly the best **available priced** route, not a global claim. Offline previews contain a dated market snapshot. No standing CP refresh or separate item-price editor is added.

All-CP spends all complete batches. Target-then-cash spends only enough batches to reach the chosen target. The split route spends a fraction of complete batches. Mixed stocks spend the cheapest selected cash value per 900 EXP first. All three byproducts yield the same 900 EXP per batch, so this ordering minimizes foregone priced cash for a fixed batch count. It is not a globally optimal future-income policy. Reward choices are alternatives; do not add every reward's cash proceeds together. Market price is not guaranteed liquidation: large quantities may sell slowly, and current quotes are frozen within a displayed scenario.

## Simulations without invented profit

CP does not inherently produce silver. The default extra income is **zero**. User assumptions define the incremental net silver per **new deployed** CP per day, a deployment cap, a setup delay and the horizon. Existing worker income is excluded from both routes because it does not change this decision.

`extra daily income = min(new whole CP, deployment cap) × incremental silver / CP / day`.

`extra income = extra daily income × max(0, horizon − setup delay)`.

`scenario outcome = retained initial cash + extra income`.

`CP opportunity cost = all-cash proceeds − retained initial cash`.

`break-even days = setup delay + opportunity cost / extra daily income`, undefined when extra daily income is zero.

The required-income readout reverses that formula for the chosen horizon. The worker/node/housing/farm deployment plan and its costs must be reflected in the user's net-income assumption. The model does not assume cash interest, additional byproduct generation, CP refunds, market changes or automatic worker deployment. No modeled outcome is written to loot, session silver or the tool timer. “Leads” compares the four displayed routes at the chosen horizon, not every possible split.

## One-shot OCR and bridge contract

The calculator requires **no OCR**. Manual CP/percentage/stock inputs work independently. Stock is entered manually because loot gained is not equivalent to inventory on hand across characters and storage. The optional CP snapshot never infers stock counts.

Native READ CP ONCE or browser Read CP once queues one request. After a 3-second lead-in the reader requires the actual BDO executable in front, verifies the exact crop's coverage and captures only the default HUD CP group (about 175×32 pixels at 1080p). It runs two contrast variants, one Tesseract process each, using the existing below-normal priority / one-thread wrapper and a 2.5-second timeout per process. It rechecks window geometry, foreground and coverage before accepting. Unusual UI scale or custom HUD positions may require manual input. There is no broad screen search or repeated retry.

The parser requires `unused / total (XX.XX%)`, validates unused ≤ total ≤ 599 and percentage <100, rejects multiple conflicting candidates, and requires both passes to agree on all three values. `1 / 490 (19.26%)` means **490 total CP**, not 1. Agreement is a rejection safeguard, not a guarantee against every recognition error. The accepted value is clearly last seen, editable and timestamped. Disagreement preserves all inputs. The existing OCR reader shows the actual crop and both outputs in memory while its window is open; nothing is saved or uploaded automatically.

`POST /cp-read` requires the current bridge `instance_id`, existing same-origin/Host guards and a ≤4,096-byte JSON body. It queues at most one read, rejects Lite Use, and rate-limits browser requests to 15 seconds. Existing app command consumption hands it to the Tk thread. `GET /cp-reading` returns only this last request's bounded status/diagnostic, never an image. The browser checks the returned request ID, stops after a result or 14 one-second checks, and never polls at idle. Opening CP Info reads cached prices once; explicit Refresh reuses `/craft-quotes` and its exact-name cache. Scenario state persists in browser local storage or native `cp_plan` settings, respectively; those stores are separate. Lite Use pauses this additional OCR completely. None of the loot, guild, tool timer or Big Drops scanning schedules change.

## Worked example and release checks

For **750,000 Mysterious Catalyst at 490 CP + 19.26%**:

- 75,000 complete batches → 67,500,000 CP EXP.
- Direct NPC sale → 15,000,000,000 silver, without market tax.
- All CP → approximately **567 CP + 95.86%**, gaining 77 whole CP.
- Reaching 500 CP takes **4,520 batches / 45,200 catalysts**. Selling the remaining 704,800 directly keeps **14,096,000,000 silver**. The final percentage at 500 is slightly above zero because the last whole batch carries EXP.
- A 90-day all-CP payoff against the NPC baseline requires about **2.165M extra net silver per deployed CP per day**, if all 77 CP are deployed immediately. A better material exchange raises that opportunity cost.

The private QA folder outside the repository can hold supplied screenshot validation. Never package those personal captures or logs. Release checks must include the real inline HTML, offline demo, boundary math/parity, reader budgets, origin/instance/Lite behavior, and an extracted Windows package. Do not claim all HUD layouts or live capture have been verified from a screenshot-only test.
