# 19. Integrated platform workflows

This chapter describes the 1.13.0-rc.5 candidate. Read [architecture](02-architecture.md), [storage](04-state-storage.md), [tools](06-tools.md), [economics](09-economy.md) and [bridge security](10-bridge-security.md) for the underlying contracts. The candidate keeps the existing Python/Tk runtime and Tesseract reader; the native experiment is not silently substituted.

## One source of observations

BDO visibility and reader gates come before recognition. Accepted item events enter `LootLedger`; goals, graphs, silver, sessions and the optional Fairy adapter consume those events. A graph must never manufacture loot, complete a quest or imply owned treasure. Tool durability and guild counters have their own verified models because they are not inventory observations.

The native main navigation opens Home, Workshop, Grind or Loot Reader in the same activity window. Gear, Quests and Fairy remain directly accessible. `App.open_activity` is the route map; adding a label without updating that map creates a dead destination. The Capture Setup section starts collapsed, with a visible toggle. Setup is an occasional task, not half of every working screen.

The compact header retains capture/recording state; detailed capture instructions and last-item evidence live in Live. Workshop and Home support mouse-wheel and Page Up/Down navigation. `ui_scroll.enable_page_wheel` scopes wheel input to canvas descendants and leaves tables/text/comboboxes to their own handlers. Nested economics tabs use the existing `Loot.TNotebook` theme.

`desktop/main_ui.py` constructs the compact 380×560 timer and exposes existing controller widget attributes. Advanced controls expand inside the same scrolling canvas; they do not resize the window. The detailed activity workspace defaults to 860×650. Shared buttons use six pixels of vertical padding (five for flat actions). Tool/debug windows open smaller while the full image remains inspectable. The source no longer mixes the main layout construction into OCR/controller code.

Silver, Grind, Insights, Sessions and Quests use `ui_scroll.notebook_page`. The returned outer frame remains the direct notebook child for navigation/visibility checks; controls live in the returned scrollable content. This prevents lower tables/footnotes disappearing at smaller heights. Its outer frame exposes `page_canvas` and `page_content` for geometry verification. Wheel input over a table remains assigned to that table. Other page margins/labels scroll the whole page.

## Home and quiet progress

`desktop/platform_home.py` owns the scrollable overview. It reads the existing tool status, capture status, quest model and recording session. It does not start a reader. Lite Use is explicit, including why loot and quests are paused. A session whose switch is on while capture is unavailable is described as armed with excluded time.

Home's summary is refreshed when the ledger revision, local day or saved daily goal changes. `ledger_totals` aggregates in SQLite instead of allocating the whole history in Python. `progress_totals` is the equivalent pure calculation used for cross-checks. State strings change only when needed. The daily goal uses recorded quantities, not events, silver or guessed crafting batches.

`platform_preferences.daily_goal` is saved with normal settings. `platform_achievements(key PRIMARY KEY, unlocked_at)` records lifetime unit milestones using `INSERT OR IGNORE`. Reopening, repeated refreshes and old qualifying history do not create duplicate rewards or repeat alert audio. This release uses quiet text/progress feedback without motion. Personal-best comparisons, configurable celebrations and probability-based rewards are not implemented.

## Linking a crafting session

1. In native Sessions, choose Crafting and the exact existing recipe, then start a session. This also selects Crafting mode for subsequent accepted events.
2. Open the same recipe in the paired local planner. Edit the existing yield, sale retention and per-batch other costs there.
3. The planner debounces those changes for 700 ms, checks the local bridge identity and sends one configuration only when it changes. No extra polling loop or price editor is added.
4. Workshop's Recipe session profit panel uses the current session's accepted rows, exact material quotes and linked assumptions. The refresh action requests that recipe's existing ingredient names through `PriceBook.recipe_quotes` on a background worker.
5. Finishing a session freezes its output/material quotes and linked configuration. Later price/configuration edits cannot rewrite that receipt.

Recipes remain the existing `desktop/assets/recipes.json` catalog. Unknown/custom recipe identifiers are rejected by the model endpoint rather than mapped approximately. Missing or ambiguous native recipe names remain unavailable. The recipe catalog is cached once; it is not repeatedly parsed in each tick.

## Model and formulas

`desktop/craft_economy.py` owns validation, persistence, calculation and the native view. For recorded main-output quantity Q, expected yield Y, ingredient quantity m and quote p:

```text
estimated batches = Q / Y
modeled ingredient quantity = estimated batches × m
modeled ingredient cost = estimated batches × sum(m × p)
gross = sum(recorded output quantity × exact cached unit quote)
retained proceeds = gross × retention percent / 100
modeled net = retained proceeds − ingredient cost − batches × other cost per batch
modeled net per observed hour = modeled net × 3600 / observed seconds
```

Rates appear only after 60 observed seconds. Excluded wall time is displayed separately. Quantity and value from priced rare/byproduct observations contribute to gross; they do not stand in for main-output batches. No material inventory change or confirmed sale is measured. A partial/missed OCR history lowers the observed output and can bias modeled batch counts. The label and basis string must preserve that limitation.

Missing linked assumptions, material prices, main output or any output price withhold net profit. Do not substitute bundled fallback prices or turn an unknown into zero. Exact cached NPC/vendor quotes already supported by PriceBook may be used with their existing source labels. The separate Manual daily estimate panel retains explicit daily costs as a fallback; never add its result to a recipe session's profit.

The native profit graph is at most 48 points, built from recorded timestamps and the same formula. Purple is gross and green is modeled net; textual amounts remain available for readers who cannot distinguish the colors. No chart library, animation, capture or web view is added to the native runtime.

## Bridge contract

`POST /craft-model` accepts a JSON object:

```json
{"instance_id":"current bridge identity","recipe_id":"existing recipe id","yield":2.5,"retention":84.5,"extra":0}
```

It uses the existing bounded JSON POST handling, loopback binding, host/origin restrictions and 4096-byte ordinary-body limit. `instance_id` must equal the current server identity. The recipe must exist. Yield must be finite and between 0.01 and 100, retention between 0 and 100, and extra between 0 and 1e12. Booleans are not numbers in this contract. A foreign Origin is forbidden; an old instance is a conflict; an absent price service is unavailable. No arbitrary SQL or path comes from the browser.

The frontend implementation exists in both `desktop/assets/crafting-studio.js` and the shipped inline planner script. Preserve both through the documented planner build ownership. The adapter only runs from localhost/127.0.0.1. A downloaded demo does not silently call the user's bridge.

Additive tables:

| Table | Key | Payload |
| --- | --- | --- |
| craft_models | recipe_id | Validated current yield/retention/extra JSON |
| craft_session_models | session_id | Configuration JSON frozen when a crafting session finishes |
| platform_achievements | key | Persistent unlock timestamp |

`insight_sessions.price_snapshot` retains frozen output and material quote objects. Old sessions without a saved model remain readable, with no invented cost basis. These additions do not replace or edit existing loot rows. Finish-time quote/model snapshots are local assumptions, not financial transactions.

## Tool numeric safety

Two numeric preprocessing passes can agree on the same clipped leading digit. `counter_context_error` therefore checks fresh independent full-label/bar context before accepting either a newly recognized value or an exact-pixel cache hit. A full-label disagreement beyond `max(4, maximum × 0.015)`, a conflicting independently located counter, or a bar-fill discrepancy above six percentage points rejects the observation. This can withhold a good read when the bar/context is damaged; it must not repair digits by expectation.

Successful verification removes transient coarse/bar hints from the retained region. Otherwise a coarse discovery value would become a stale veto against normal declining durability. The numeric cache remains bounded and time-limited. A large same-field decrease schedules fresh discovery on the next normal scan. The application also guards a large downward identity change until repeated use evidence; a manual fresh scan is explicit. Place Mode still provides the initial positional choice, and use confirmation remains independent.

`white_glyph_mask` is shared by title-motion signatures and gold-bar candidate filtering. A candidate with fewer than 12 white glyph pixels is skipped before starting OCR; it cannot supply a readable white tool title. This is a cheap candidate filter, not digit recognition or a looser numeric acceptance rule. `unreadable_regions` also ignores a numberless partial-title hint centered inside an already verified numeric field; separate or conflicting numeric fields remain reported.

When damaged-separator digit boxes fail, a bounded fallback reads the whole white-glyph numeric field twice. Both passes must contain the same complete literal pair and agree with an independently measured bar fill. The malformed HOCR pair used to locate the failed split is not a numeric veto for this fallback. No character is replaced or dropped to manufacture a fraction. A successful field retains white-glyph preprocessing for subsequent two-pass reads, avoiding another four failed split-field attempts each time.

Failure evidence includes the crop, numeric/raw output, independent context and rejection reason. Cache acceptance clears an earlier rejection label. The real-Tesseract matrix tests several font sizes and leading-digit values; every accepted fixture must be exact. Synthetic tests are not proof of universal BDO font/scale accuracy. Keep live camera movement, identical tools, near-zero replacement, refills, occlusion and delayed-read cases in the acceptance matrix.

## Lite Use work budget

After the initial tool reading needed for the timer, Lite Use pauses all automatic OCR. In `LootInsights.tick`, entering Lite mode publishes paused state and saves the clock once. Subsequent ticks do not query capture availability, refresh market quotes, republish the ledger or repeatedly save the session. Visible Home may update cheap status text. The existing one-second callback remains; there is no replacement polling service.

When returning to normal tracking, clock gates exclude the paused interval. Closing also ticks the capture clock unavailable before persistence. An in-flight OCR task may finish, but stale-generation results remain discarded by the existing reader gates. `test_lite_budget.py` exercises 100 consecutive Lite ticks and verifies the expensive calls happen zero times after the transition. This is a work-count regression, not a promise of zero CPU or RAM.

`scripts/benchmark_platform.py` measures synthetic domain calculations over 20,000 events. It reports median/p95 and Python allocations, excluding input construction. It does not include Tk, OCR subprocesses, whole-process memory, game FPS or real capture. Use the existing performance tools for those separate questions.

## Fairy run review

`scripts/build_fairy.py` preserves the pinned upstream page and adds a small adapter. Its completed-run picker offers up to 30 native Grind receipts from the shared snapshot. Review displays observed/excluded time, recorded item value, partial-price status and units. Saving after confirmation writes a journal entry to the selected Fairy vault through `VisionImportReceipt`.

The stable key contains the Vision history identity and session identity, so a repeated snapshot or click cannot duplicate a receipt. Kill count remains unknown. The adapter does not add a simulated Fairy session, change collection ownership, convert pity or pretend all recorded drops are still owned. Existing exact-name loot linking remains separate. Public and localhost browser vaults still require explicit export/import because their origins differ. See [Fairy integration](../FAIRY-CODEX.md).

## Extending and validating

For another progress metric, prefer an aggregate over accepted ledger data and a version-based refresh key. For a new crafting assumption, update validation, freeze it in receipts, expose its basis, cover missing inputs, and edit both planner sources. For another run export, choose a stable identity and a reviewed destination; do not accumulate snapshots as new events.

Run `python dev.py test tool_reader tracking_core craft_economy platform_progress lite_budget fairy_integration ui_smoke`, then `python dev.py check`. Developer and test launches seed an empty database before app startup so legacy migration cannot import the real history into a disposable profile. Explicit migration tests still exercise the production migration path.

Before distribution, build from a clean committed revision, check the extracted Windows ZIP, verify its manifest/checksum, preserve older artifacts, and use the locked installer with a SQLite-consistent backup. Live acceptance is a separate record. Do not label a candidate universally accurate because the regression suite passed.
