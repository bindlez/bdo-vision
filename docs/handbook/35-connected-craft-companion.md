# 35 · Connected craft companion and event snapshots

See [the user test guide](../COMPANION-TEST.md). rc.28 is a test candidate, not a
claim of complete inventory recognition or universal live OCR accuracy.

## Shared calculation ownership

`craft_panel.py` is a Tk input/presentation sidecar. It lazily reads the existing
recipe catalog, searches at most 30 cooking/alchemy variants and submits one
replaceable request to `PlannerBridge.request_craft_panel`. It contains no second
recipe, mastery, sale-tax, weight or profit calculator. Replies are validated by
`craft_panel_contract.py` before reaching native widgets. Current LT is the weight
before **extra packing**; unknown existing ingredient stacks are not subtracted.

`visionCraftPanelCalculate` in `crafting-loot-view.js` uses the actual shared
`VisionCraft` engine and the website's saved character/recipe assumptions. Linked
editing uses `ingredientRatio`; independent editing uses the limiting entered
quantity. `carry` supplies capacity/fit, and `plan` supplies costs and expected
outputs. Missing prices leave money unknown while quantities remain available.
The existing five-minute shared price request cache fills missing quotes on demand.
The sidecar displays the market-model assumptions and planned duration explicitly.

The current verified tool's remaining countdown supplies the default use budget;
explicit edits become manual budgets. A captured current craft family is selected
on opening only when it belongs to the active native tool session. The complete
website planner's independent cooking/alchemy stopping preferences are preserved.

## Request and timer protocol

`/durability` retains its original fields and includes the pending request. The
dedicated `#companion` tab also opens `/craft-panel-events`: one active, same-origin
event stream, with a sleeping condition variable and a 20-second heartbeat.
Native edits wake it immediately, avoiding reliance on background browser timers.
Opening a newer stream replaces the older subscriber; old clients close on error
rather than fight to reconnect. A closed/frozen browser still requires reopening
the dedicated tab. No browser runtime is embedded or installed.

`POST /craft-panel-result` requires the current instance and request IDs, finite
bounded JSON and valid recipe/ingredient/count fields. Stale replies are rejected.
The server consumes the start flag on acknowledgement. Only an explicit native
TIMER click requests a planning timer. The browser requires a positive fitting
load, deduplicates retries through a saved timer request ID and rejects starts
older than 15 seconds. Closing the panel cancels its outstanding request. No game
input, crafting action or loot write occurs through this protocol.

The main HUD switches to remaining utensil uses/time while a craft countdown is
active without a grind session. Its estimates assume crafting continues. Overlay settings can show recorded craft loot for the current tool session
beside the durability countdown. The sidecar moves with its parent on drag and release, reselects the parent's monitor,
and stays scrollable on short displays. Drop reveals tile around both rectangles.
The search sidecar intentionally accepts focus; the HUD and drop reveals remain
passive. It cannot type into BDO on behalf of the user.

## Inventory scope and safety

`inventory_reader.py` observes the I-key edge only when explicitly enabled.
The optional observer checks the key every 40 ms, without intercepting it; Lite
Use reduces this to a sleeping one-second state check and prevents all captures.
It schedules one capture 600 ms after an edge. Manual reads wait 1.8 seconds.
It skips busy readers, verifies foreground BDO identity and verifies that the
actual Inventory heading and complete Weight row are not covered before accepting.

One bounded coarse Windows read locates the widget. A tightly scoped source-scale
row crop is then independently read by Windows OCR and Tesseract PSM 7. The exact
current/maximum numbers must agree. Tooltip unit weights lack the carried/max
ratio and cannot satisfy the parser. Numeric digits are never repaired. Source
images remain in memory; the optional Inventory reader uses the shared debug view.

The snapshot stores only timestamp, carried/max LT, partial scope and an empty
item list. **Icon identities and stack quantities remain unknown.** It is not a
complete inventory scan. The file is bounded, written atomically and included in
profile backups. It never modifies the loot ledger. Applying it in the sidecar is
explicit, with the last-seen timestamp; later bag changes require another read.

Three privately held screenshots produced cross-engine matching values in about
0.43–0.47 seconds each on this machine. Those frames are not published. The evidence
does not establish all resolutions, UI scales, languages or live opening behavior.

## Forecasts and celebrations

The existing craft-inference engine retains recorded quantities. Gap forecasts can
be disabled independently. Lite Use may display model estimates for the same
verified tool without running OCR. Browser remaining-value updates require a
matching tool session and fresh native timer context. Projected units/value never
enter the ledger. The existing captured-rate denominator continues excluding
unreadable time.

Optional craft milestones use accepted captured units at 100, 500, 1,000, 2,500,
5,000, 10,000, 25,000 and 50,000. The highest announced milestone is stored in the
existing craft run, preventing restart replay. They use the bounded reveal queue
and existing mute/motion/sound preferences, but are not Big Drop journal entries.

## Sessions, Fairy and CP

New grind session labels are generated from local start date/time. `grind_details`
owns the separate spot; `grind_identity` stores automatic mode and a bounded exact
trash-evidence set across restarts. Shared rare drops never prove a location.
The initial signatures are deliberately narrow: Tungrad Ruins Fragment and Corrupt
Power Source. Unknown or contradictory evidence stays unresolved; the readonly
spot selector permits supported overrides. Broader spot coverage needs a verified
signature catalog, not fuzzy matching against arbitrary loot names. Treasure
pursuit remains optional, with curated suggestions; no piece variant is inferred.

Reference checks: [Tungrad trash item](https://bdocodex.com/us/item/65328/) and
[Corrupt Power Source zone table](https://www.blackdesertfoundry.com/global-lab-updates-21st-november-2025/).
These identify signatures, not future prices or drop probabilities.

`fairy_desktop.py` presents a **read-only** compact treasure catalog and recorded
treasure-family finds. The website retains the full vault, simulators and ownership
state; native observations do not fabricate owned parts. Generate its shared JSON
using `node scripts/build_fairy_catalog.js`; parity tests compare all 12 records
against the website's source catalog.

Native CP adds byproduct EXP and stock opportunity-cost pies from the existing
report, retaining target charts and the full website shortcut. No CP formulas or
market-price stores are duplicated.

## Verification and open acceptance

`test_companion.py` checks widget construction, native/browser request plumbing,
stale/origin rejection, event delivery, inventory parser guards, Lite Use, persistent
spot evidence, catalog access and CP chart rendering. `test_craft_companion.js`
checks shared-engine quantities, independent limits, native cadence, invalid inputs,
timer retry/expiry guards and catalog parity. Both run in the full release checks.

Live I-key opening, current tool/recipe transitions, actual timer completion,
background-browser behavior and mixed-DPI/fullscreen docking still require user
acceptance. Complete inventory item recognition and a native replica of the full
Fairy vault are not implemented in this candidate; their website features remain
available and unchanged. This scope is deliberate and must remain explicit.

## rc.29 craft essentials and countdown boundary

`guild_summary.py` formats the same retained `GuildQuestProgress.snapshot()` for
native dashboard and live HUD. The dashboard updates with existing tool-view
refreshes; the HUD with existing live ticks. No reader, timer or bridge poll is
created. A completed snapshot stays labeled last-seen; a stale numeric snapshot
is not promoted to a fresh observation. The website automatic craft card uses
`visionCraftStatusModel` and the existing `guild_status` payload.

The paired guild read still runs immediately after each completed tool attempt,
including Lite Use's acquisition, under the existing visibility and OCR gates.
It does not wait for a second timer cycle. User-enabled Smart Watch remains
optional; this release does not silently enable background OCR.

`change_craft_speed` settles elapsed monotonic time at the old pace before setting
a new pace and re-sending a linked planner snapshot. Compact pause/resume keeps
remaining fractional durability and the tool session. Covered capture cannot
prove progress: forecasts continue at the displayed pace, while recorded loot
remains observation-only. The reported early alarm needs a real-game comparison;
no guaranteed hidden-game timing is claimed.

`visionRevealActiveTimer` opens the existing timer workspace and focuses the
conflicting card. Its Cancel button remains an explicit user action. The central
`startCraft` guard also protects direct starts; native companion requests reject
a conflicting start rather than falsely reporting a new timer.

CP target inputs and calculations are unchanged. `cpShowSection` switches between
route comparisons and the full target planner without modifying the scenario.
