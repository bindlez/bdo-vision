## 1.13.0-rc.40 — Grind capture and loot recovery

- Start Grind enables recording and arms the configured loot capture area. Confirmed drops stay in the active run if the area is covered after capture.
- Recognize verified grind trash without requiring a Central Market listing. Recover noisy personal System receipts and keep agreed popup drops if an optional OCR pass times out.
- Added a paired-feed benchmark for independently labeled drop sequences. A correct result requires the item and exact count, with extras and misses scored separately.

## 1.13.0-rc.39 — Shared craft state

- Dock and Tracking use the same craft phases. Loot uses the accepted tool from that state. Guild quest estimates use its capture fallback signal.
- Pausing blocks automatic tool scans until resume or an explicit scan. Delayed and in-flight scan results from before a pause, resume, or manual start cannot change the timer.
- Starting or resuming Grind gives it the dock and loot reader without requiring a craft tool. Detailed Craft stays available when switching back.

## 1.13.0-rc.38 — Dock timer and active tool verification

- Dock 0 shows durability and time in Detailed Craft Tracking, even with a grind session still open. The separate craft loot panel keeps its silver and graphs.
- Detailed tracking looks for durability use across verified visible tools. Position alone cannot attach craft loot to a tool. The reader retries quickly when it can read a counter but needs more evidence.
- Scan tool now and Tool reader status are available from the dock Apps menu.

## 1.13.0-rc.37 — Craft metrics and Screenshot Lab

- Detailed Craft Tracking adds a compact docked panel with captured value, estimated silver per hour, and the top captured items. It shares the existing tracker and yields to configured capture regions.
- When no tool is verified, detailed tracking retries sooner and lets the tool scan take the next available reader slot when due.
- Screenshot Lab opens one separate Tier −1 process. Review local gear slots and inventory grids with exact reference icon matching. Unknown or ambiguous icons need review. Closing the window clears the workspace.

## 1.13.0-rc.36 — Detailed craft tracking and estimated quest alerts

- Timer-only mode can estimate when to check a guild quest using verified progress or an entered units-per-craft assumption. It never marks estimated completion as verified.
- Detailed mode rechecks visible tools and guild cards, records configured craft loot, and corrects timer drift over 15 seconds after a verified read. Unavailable capture returns the timer to estimates.
- A second verified Complete reading after at least 20 seconds can remind the user to claim a mission.

## 1.13.0-rc.35 — Dock-first desktop

- Vision opens on the dock. Tracking opens the existing MainWin beside it.
- Native Craft and workspace panels switch in one attached slot. Closing a panel preserves active tracking. Click-through startup keeps MainWin reachable.
- The Apps menu opens browser tools and provides an explicit Exit Vision command.

## 1.13.0-rc.34 — Live market and recipe workspace

- The web planner can fetch current NA and EU base-item quotes directly. Market lookup includes stock, last sale, lifetime trade count, and price history.
- Market shares its exact-ID quotes with recipe costs, shopping, production, and saved plans.
- Recipe Planner groups the existing tools into Overview, Ingredients, Production, Results, and Queue. Refresh prices and launch timers from the recipe header.

## 1.13.0-rc.33 — Crafting and Central Market workbench

- Inspect a craft item's regional quote, stock, makers and consumers by exact ID.
- Open the recipe's shopping basket to see quantities, stock shortfalls and required cash after owned stock.
- Compare modeled unit cost with the buy quote. Keep unknown prices and volume explicit.
- Separate Processing methods from Imperial crates. Show recipe economics on search cards and expose the full stage weight board from the recipe header.

## 1.13.0-rc.32 — Tool and loot reader coordination

- Withhold tool selection when competing counters conflict. Keep the previous timer as an estimate.
- Serialize tool and loot work, bound attempts, and discard late results.
- Bind craft loot attribution to the tool session present when the frame was captured.

## 1.13.0-rc.31 — Early craft estimates and Vision dock

- Craft silver/hour estimates start after 10 readable seconds. The existing reader temporarily shortens its interval for a new verified craft tool.
- Desktop workspaces use a shared slate and teal theme. Open native workspaces and the planner from the Vision/Grind overlay's Apps menu.

## 1.13.0-rc.30 — Tool-sized timers and inventory preview

- Recipe timers split at the configured full-tool capacity, from 3,000 to 5,000 uses.
- Crafting previews time and Life EXP from saved or pasted inventory counts.
- The craft overlay can show recorded craft loot next to durability.
- Desktop CP Intelligence exposes both calculation methods. Website CP opens on routes and break-even, with a separate target tab.
- Quest settings explain how to get completion and missing-mission reminders between paired scans.

## 1.13.0-rc.29 — Craft essentials and accessible timers

- Last-seen guild counter / completion beside desktop tool durability, in the
  overlay, and in the automatic Current Craft card. No extra OCR loops.
- Open the existing timer directly when a craft start conflicts; Cancel is on
  that card. Recorded loot history stays intact.
- CP opens with route comparisons again; Reach my target CP has its own section.
- Crafting grid and form width containment; earlier single-column layout.
- Compact craft pace and pause/resume controls. Pace changes preserve old elapsed
  time; resume preserves remaining uses. Covered-game timing is explicitly an
  estimate and still needs live comparison against actual tool consumption.

# 1.13.0-rc.28 - Connected crafting companion (test candidate)

- Native CRAFT sidecar: real recipe search, linked/independent quantities, max
  packing, weight/tool limits, outputs, expected silver and explicit timer starts.
  The dedicated paired website tab owns the calculation engine; event-driven
  requests support background use without adding a capture or polling loop.
- Optional I-key inventory snapshots verify the Inventory/Weight widget, locate
  its row and cross-check Windows OCR with Tesseract. Currently weight only:
  icon identities and stack quantities remain unknown. Lite Use prevents capture.
  Includes a live Inventory reader/debug view and local snapshot backup.
- Craft forecasts remain separate from observed loot, can be disabled for gaps,
  and use matching tool sessions for remaining-value estimates. Lite Use retains
  estimates without enabling capture. Optional captured-unit milestone reveals.
- Timestamped grind session names; separate spot inference from two exact trash
  signatures, ambiguity handling, a spot selector and persisted evidence. The
  initial signatures cover Tungrad Ruins and Yzrahid Highlands; unknown stays unknown.
- Added compact read-only Fairy treasure desk from the shared 12-treasure catalog,
  recorded treasure-family finds and a full-vault shortcut. Website ownership is
  retained; native view does not infer piece variants or duplicate vault ownership.
- Added CP byproduct EXP and opportunity-cost pies using existing scenario data.
- All prior features and history retained. Live inventory opening, actual craft
  timing and fullscreen/mixed-display overlay behavior still need game testing.

# 1.13.0-rc.27 - A visible crafting desk and game overlays

- Kept all original features/pages; replaced native destination menus with visible
  groups and destination buttons, plus direct website Crafting/CP/Imperial links.
- Open crafting overview and ingredients by default, with a persistent quick-access
  bar for weight, map/timeline, production, outputs, tax, graphs, character and queue.
  Searchable recipes stay visible by default; calculations and timers are preserved.
- Added a website live context strip for tool/time, automatic craft, loot capture
  health and last-seen guild status through the existing bridge poll. Sharing stays optional.
- Added compact passive game HUD, saved monitor-aware snapping and drag feedback,
  dock buttons, click-through lock, tiled Big/Huge/Treasure reveals, bounded queue,
  optional sound, reduced motion, snooze and synthetic preview controls.
- Fresh guild completion now prompts for the next mission when crafting begins;
  state checks use the existing tick, and sound is deduplicated. Unknown remains unknown.
- Incomplete personal-loot reads get bounded two-pass physical-row recovery using
  the existing Windows helper. One private eight-row failure now reads eight exact
  rows instead of five; that replay took 0.75s, not a live accuracy/FPS guarantee.
- No new runtime dependency, background capture loop or gameplay input. User history
  is unchanged. Live drop recall, mixed-DPI snapping and quest alerts need game acceptance.

# 1.13.0-rc.26 - Map-first production planning

- Replaced the planner's primary screen with a connected recipe map, visible future
  products, a goal selector, ordered relative timeline and clickable stage details.
- Introduced a canonical cached item/recipe network shared by the planner: exact
  input slots, substitution conversions, main/rare producers and reverse consumers.
- Goal previews preserve the selected product's actual recipe/substitutions and
  leave saved inventory, Make/Buy choices and packing targets untouched.
- Stage timers use exact direct-input models and retain duplicate/chunk guards.
  Previous packing, economics and workshop tools remain in a disclosure underneath.
- Cooking and alchemy now have separate saved run limits: both default to current
  tool durability, with ingredient-only, hybrid-first-limit and manual alternatives.
  Reuse the existing tool feed; no new OCR or polling.
- Verified all 990 variants and actual Fruit Wine/Meal connections; no invented
  Fruit Wine-to-Balenos route. No new OCR, polling or runtime dependency.

# 1.13.0-rc.25 - Isolated starting-stock simulator and Crafting workspaces

- Added a separate whole-chain simulator: choose a final product and any upstream
  raw material or intermediate as the starting stock. Buy missing companions or
  require entered stock only, with shared branch allocation and fixed source supply.
- Show stages, expected final/side outputs, purchases, leftovers, one-more-craft
  limits, lazy time/cost graphs and labeled scenario export. Unknown prices remain
  unvalued; current packing, queues, inventory and timers are never edited.
- Separated Recipe planner, Chain simulator, Imperial turn-ins and Timers into
  focused workspaces, preserving the timer engine and exposing its active count.
- Added an optional large-chain card grid with expandable ingredient sidebar and
  full-make economics/time summary; it does not change the current planning route.
- No new OCR, runtime dependency or background polling. Added isolated-state and
  real shipped-UI regression coverage plus a standalone simulator preview.

# 1.13.0-rc.24 - Connected production line and linked packing

- Put the complete selected recipe chain above economics, with preparation-order
  steps, explicit feeds-to relationships, capacity badges and compact packing cards.
- Edit any ingredient to snap its companions to whole-craft ratios. Show leftovers,
  modeled LT fit/overflow and per-load timer guards; max-fill is one click.
- Use one normalized item/recipe graph with ID-based edges, selected substitutions,
  variants, cycle guards and bounded traversal. Existing downstream uses remain
  connected to the ordered production queue; no duplicated nested recipe catalog.
- Added real Sungnyung / Nurungji / Cooked Rice UI and graph regressions.
- No new runtime dependency, OCR call, capture or background polling.

# 1.13.0-rc.23 · Carry loads and forward production planning

- Added a weight-based packing calculator: entered max/current/reserved LT,
  optional carried ingredient quantities/tool limit, exact additional grab list,
  output accumulation models, load time, charts and export.
- Added cooking recipe rankings for longest carry run, most crafts per load and
  lightest ingredients, using the same character limits and recipe assumptions.
- Added downstream normal/rare product discovery, substitution-aware consumers,
  bounded multi-stage paths and production-route queueing.
- Kept outputs now feed subsequent plans once, without also counting them as
  sold. Added queue ordering and modeled remaining-stock balances.
- No OCR, weight polling or live inventory mutations added. Existing automatic
  crafting and tool/quest/loot behavior is preserved.

# 1.13.0-rc.22 · Automatic current-craft intelligence

- Detect cooking/alchemy recipe families from repeated accepted output and a
  verified active utensil. No recipe/session selection or Crafting mode needed.
- Show captured item value/hour, expected main+rare value/hour, scanned-tool value
  and remaining-durability value, plus explicit modeled ingredient-profit ranges.
- Add bounded current-price value graphs, output/coverage donuts and captured-unit
  milestones. Share the detected craft with the paired site only when sharing is on.
- Save inferred runs and event membership separately; never rewrite accepted
  quantities or original activity labels. Derive automatic craft labels for views
  and include those accepted events in optional crafting-timer earnings.
- Reuse the existing app tick and OCR. Exact recipe price lookup is cached and
  backgrounded. Capture gaps freeze measured time; Lite Use stops inference/extra OCR.

# 1.13.0-rc.21 · Simpler navigation and next actions

- Replaced the crowded desktop tab strip with Home/Craft/Grind/Quests and grouped
  Planning, History and Readers menus. All original page routes remain available.
- Workspace opens at Home and preserves your page when reopened. Loot tracking
  stays visible beside its status; redundant Home/footer navigation was removed.
- Cooking now leads with the next stage. Full stage lists, route comparisons and
  extra actions expand on request. The main timer action cannot skip intermediates.
- Native CP target graphs and Grind goal/streaming setup expand when wanted.
- No history schema, valuation, OCR decision or capture scheduling changes.

# 1.13.0-rc.20 · Cooking execution and richer session views

- Added explicit next-stage planning timers, duplicate-launch prevention and
  bounded full-chain lowest-priced substitution choices. Deep real meals and
  the exact Organic Feed variant are covered by shipped-page interaction tests.
- Added budget, time and expected-output donut charts and a teal palette accent.
- Added a dedicated cooking preview and manual acquisition guards for unknown
  processing methods; make-all avoids automatically selecting these exchanges.
- Added a compact native live grind window and independently opted-in local OBS
  output, with optional clock/loot widgets and stale/offline clearing.
- Added silver goals, current-price personal-best pacing, loot-value and
  observed/excluded-time donuts. No new OCR loops or chart packages.
- Recorded competitor gaps explicitly; this is not a claim of full app parity.

# 1.13.0-rc.19 · Multilevel cooking and alchemy workshop

- Added a production workshop with make-all/buy routes, recursive recipe choices,
  ordered intermediate batches, exact per-stage inputs and retained surplus.
- Added cash/economic-cost/time/profit route comparison, stage-time visualization,
  priced purchase bars and full production runbook export.
- Added a sequential manual preparation checklist with milestones. Changed stage
  quantities reset progress; checkboxes never write inventory, loot or earnings.
- Preserved recipe, mastery, rare yield, tax, processing, Imperial and queue models.
- No OCR decision behavior changed. Core reader regressions are required; these
  checks do not establish a live accuracy percentage.

# 1.13.0-rc.18 · CP targets, native Imperial and Workerman payback

- Added inverse target CP planning: each byproduct alone, owned mix, completed
  mix and balanced mix, with exact bundles, shortages, leftovers and opportunity cost.
- Added per-byproduct target lines and owned EXP coverage pies in browser and native CP.
- Expanded native CP with exchanges, curve, custom split, frontier, income stress
  graph, simulation recovery slider, affordable-target and payback-income solvers.
- Added the native Imperial tab with four recommendations, mastery, shared current
  CP, Guru filter, costs/payout/profit/daily totals and lazy advanced details/graphs.
- Native/browser Imperial calculations share data and are parity-tested across
  real recipes, mastery levels and stock conditions. Planning adds no OCR or polling.
- Added optional Workerman CP payback: pinned public reference, exact-ID cached
  market prices, full-job CP gating, declared costs/uptime, break-even days and
  recovery graphs in native CP Info and the paired browser. No extra OCR or polling.
- Preserved rc.17's structured core route and safe missing-quest reminders.

# 1.13.0-rc.17 · Structured core reader candidate

- Added a lazy, persistent positioned Windows OCR worker and independent numeric/
  guild-card verification, with conservative compatibility fallback.
- Recovery handles damaged utensil titles without repairing numeric values;
  cooking/alchemy guild headings and wrapped counters remain scoped.
- Optional missing-matching-quest reminders reuse existing acquisitions, distinguish
  unreadable from confirmed absence, deduplicate and support ten-minute snooze.
- Added the saved Guru-only Imperial filter and a complete prioritized task list.
- 392 Python regressions passed. Saved/live-reference checks are scoped evidence;
  a changing installed-game run and broader held-out acceptance remain open.

# 1.13.0-rc.16 · Stock-aware Imperial daily planning

- Four recommendations separate overall and fully stocked buy/craft choices.
- Available crafting variants/substitutions and NPC purchase fallback are priced
  independently; unknown stock never qualifies as available.
- Remembered total CP sets the daily allowance and whole-run crafting costs;
  per-box and potential daily profit/payout are shown separately.
- Added items per box, turn-in silver, and lazy advanced profit graphs,
  ingredient breakdowns, expected surplus and return on input cost.

# 1.13.0-rc.15 · Simpler Imperial comparisons

- Cooking/Alchemy tabs and one remembered mastery input, with all tiers compared.
- Buy and craft profit side by side; clickable descending profit rankings and
  two best-option summaries. Missing prices and stock warnings remain explicit.
- Removed tier and daily quantity setup from the quick comparison.

# 1.13.0-rc.14 · Imperial quick picks

- Four compact, cost-sorted Imperial turn-in lists: buy/craft cooking and alchemy.
- Tier, mastery and daily quantity controls; exact-ID cached quotes, stock warnings,
  whole expected crafting batches and profit after acquisition cost.
- Shared on-demand market refresh; no additional OCR, polling or dependencies.
- Calculation and shipped-page controls covered by regression checks.

# 1.13.0-rc.13 · Crafting Intelligence and market-first CP

- Replaced the mixed 114-entry recipe book with 990 attributed variants and 105 concrete substitution groups; compatible saved IDs are preserved.
- Added processing/imperial methods, mastery models, normal/rare/optional extra outputs, tax benefits, owned stock, recursive make/buy, production trees, shared queue surplus, EXP/weight, market-volume filters and lazy SVG analysis.
- Selected-plan quotes use exact item IDs and the existing cache. An optional streamed whole-recipe market snapshot adds fourteen-day daily-average volume, with bounded requests and no polling/OCR loop.
- CP defaults to material exchanges; NPC selling is optional. Unknown market opportunities withhold payoff/graphs; leftovers remain in inventory. Offline previews use dated prices, never a simulated live feed.
- Shared models link resolved ingredients, region and locked recursive input costs into native sessions. Removed redundant legacy profit controls and independent fallback arithmetic.
- Added a linked Markdown-backed project paper with explicit fictional narrative disclosure and scoped evidence, plus developer documentation and a reference matrix.

# BDO Vision Lite changelog

## 1.13.0-rc.12 · Payback planning and reader acquisition

- Add deep CP forecasts, ramp-up / utilization / setup assumptions, constrained target search, recovery graphs, scenario milestones and native-to-browser scenario import.
- Prioritize Place Mode/bar tool acquisition; preserve current bar evidence and discard digit boxes after one frame to prevent clipped future counters.
- Read full-width scoped quest cards first, queue busy paired reads, expose actionable states and add explicit opt-in Smart watch without changing Lite behavior.
- Keep standalone runtime packaging, existing features, profile history and prior immutable archives.


## 1.13.0-rc.11 · CP Intelligence

- Add native CP Info and integrated browser CP planner with current post-2025 EXP brackets, byproduct exchanges, cash/CP/target/split allocations and source links.
- Reuse exact-name Central Market pricing, keep unknown rewards explicit, apply market tax only to market routes and account for batch leftovers.
- Add scenario income/deployment/delay controls, break-even, target distance, SVG graphs and an interactive offline demo without live screen access.
- Add explicit small-crop two-pass CP HUD reading, in-memory OCR debugging, Lite safeguards, rate limits and no recurring capture or price loop.
- Add native/browser parity regressions and a detailed CP developer chapter. Preserve the previous immutable release packages.

## 1.13.0-rc.10 · Big Drops

- Add strict individual-price Big (>1B) and Huge (>10B) tiers plus curated treasure/spotlight recognition.
- Add a deduplicated local trophy journal, original observed moment timing, personal rarity shelf, retrospective pace/burst heat, native reveals and shared website cards.
- Reuse accepted loot, capture clocks, cached market prices and existing update loops. Preserve Lite/timer scan shutdown and paired last-seen quests.
- Add an offline interactive sample preview, renderer ownership/security checks and native/rule/persistence/work-count regressions.

## 1.13.0-rc.9 · scan once and retain the countdown

- Preserve running estimates on a lost active-tool match; never start or resume a timer from an unreadable scan.
- Stop automatic tool OCR after confirmed use until zero; keep Lite Use OCR off after its initial reading and after expiry.
- Pair optional guild snapshots with tool attempts, reuse full captures, keep quests last seen and remove independent quest polling.
- Separate located-but-unreadable tool labels from no labels detected. Reduce Lite idle work and add integrated controller lifecycle regressions.

## 1.13.0-rc.8 · completed guild widget and camera-angle recovery

- Detect the literal completed guild widget in two existing passes; retain numeric last-seen values, persist/deduplicate completion, and guard new-mission transitions.
- Show completion in Quests, Home, debug output and frozen planner timer receipts, including when no counter was previously observed.
- Recover failed residence/label OCR with bounded white-glyph fallbacks and nearby labels above Place Mode; reject nonzero crops conflicting with an empty-tool discovery counter.
- Add real synthetic OCR and parser/state/UI/bridge/rendering regressions. Private live captures remain excluded from release files.

## 1.13.0-rc.7 · compact startup

- Enabled loot tracking no longer opens the large workspace automatically; detailed views open on demand.
- Kept background capture enabled and added a native startup regression.
- Includes the protected tool-reader and compact interface fixes from rc.6.

## 1.13.0-rc.6 · fragmentary bar confidence

- Keep short/transparent dark-track fragments usable as label locators without trusting their distorted fill percentage.
- Recovered the saved near-empty 353/5000 tool frame; numeric agreement and established discovery remain unchanged.
- Added the fragmentary-track regression and retained the compact rc.5 interface.

## 1.13.0-rc.5 · compact tracker and cheaper discovery

- Reduced default main/workspace sizes, spacing, buttons, debug previews and heading sizes; advanced main controls expand on demand.
- Separated the main layout into readable main_ui.py without changing timer, planner, tray or reader callbacks.
- Skip texture-only gold candidates before OCR and suppress duplicate partial-field miss messages; numeric consensus/context guards remain.
- Fixed Windows LF/CRLF generation differences in the reproducible Fairy page.

## 1.13.0-rc.3 · integrated platform candidate

- Unified Home with reader/session states, daily goals and persistent deduplicated milestones; collapsed occasional capture setup.
- Linked recipe session output, existing exact quotes and planner yield/tax/expense assumptions; frozen receipts and bounded gross/net graphs.
- Guarded numeric OCR/cache against fresh context conflicts and suspicious drops without inventing digits or adding regular OCR passes.
- Added reviewed, deduplicated Fairy journal receipts; retained unknown kills and separate collection ownership.
- Reduced repeated Lite-mode work, used SQLite Home aggregates and bounded shared run history; no additional runtime dependency.
- Isolated development/test histories and documented platform editing contracts in handbook chapter 19.
- Read visible version from the shipped VERSION file; reject packaged identity mismatches.

## 1.12.1-rc.1 · OCR inspection and developer edition

- Added opt-in Tool and Quest OCR image/text inspection with no independent capture loop or screenshot logging.
- Rejected empty/unverified Place Mode selections and conflicting nearby-tool timed confirmation.
- Added two-pass focused guild-body recovery for wrapped counters within the existing work budget.
- Added disposable development launches, targeted isolated tests, contributor instructions and an offline searchable handbook with source atlas and generated contract references.
- Preserved stable 1.12.0 artifacts, protected profile/history, sharing, planner and tray behavior.

## 1.0.0 · First focused release

- Built a compact dark-violet timer dashboard and custom icon.
- Simplified Scan & Track → Send Now → linked planner workflow.
- Added a guided first launch: calibrate OCR region before enabling auto-scan.
- Removed intrusive planner tab switching and repeated notifications during auto-sync.
- Corrected comma-grouped durability parsing and confirmed downward-jump tool recognition.
- Prevented settings window from covering the game during region selection.
- Distinguishes local bridge readiness from browser-acknowledged sync.
- Added scrollable Settings with persistent Save control.
- Reduced launcher dependencies: Pillow is required; tray UI automation is optional.
- Added release regression tests and build workflow.

See `RELEASE_NOTES.md` for detailed testing and limitations.
