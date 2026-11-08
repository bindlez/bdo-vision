# rc.29 tonight test checklist — November 3, 2026

- [x] Put last-seen guild progress next to native tool durability, in the live
  overlay, and in Current Craft automatic. Completion is explicit; no inferred
  quest progress or completion has been added.
- [x] Existing-timer conflicts open the Timers workspace and focus the existing
  card, with its Cancel action. Recorded loot history is not removed.
- [x] Separate Reach my target CP from the default Routes & break-even section.
- [x] Fixed live status strip occupying a recipe column: full-width grid span
  and recipe-panel selectors that survive insertion of the strip. Bound shrinking grid children and form widths; collapse the recipe desk
  before narrow columns displace the crafting controls.
- [x] Expose seconds per craft and pause/resume on the compact timer. Settle
  elapsed time at the old pace before changing future timing. Resume preserves
  fractional remaining uses and the tool session.
- [ ] Live acceptance: reproduce the reported early alarm over an extended
  covered-capture interval, compare configured pace against actual durability
  consumption, and check the guild completion and new-quest transition in BDO.
  Tests cannot establish game progress while no capture is possible. No universal
  early-alarm fix is claimed: a forecast assumes uninterrupted crafting at the
  configured seconds per use; processing overhead, game pauses and wrong pace
  remain sources of error. No extra continuous tool scans have been added.
- [x] Browser sample preview confirms aligned recipe and planner panels and CP
  section switching.
- [ ] Live acceptance: confirm readable layout at the tester's Windows scaling
  and browser zoom. Automated markup tests are not visual acceptance.

# rc.28 companion test scope - November 3, 2026

Implemented: shared-engine native crafting sidecar and explicit timers; event-driven
website link; optional cross-engine weight snapshots with debug view; gap forecasts
and opt-in captured-unit milestones; dated grind labels with two exact trash
signatures; compact read-only Fairy treasure desk; additional native CP pies.
See [the test guide](COMPANION-TEST.md) and [developer contract](handbook/35-connected-craft-companion.md).

Open acceptance: actual I-key opening and weights at the user's UI scale; live
craft timing and background browser behavior; mixed-DPI docking. Full inventory
icon/stack recognition, broad spot coverage and native Fairy vault ownership sync
remain explicit future work. Existing full website functionality is preserved.

# Current UI and reader work - November 3, 2026

See [the normalized brief and ordered checklist](UX-RELEASE-PLAN.md). rc.27 adds the
visible crafting desk, accessible native destinations, shared live context, passive
snapping overlays, quest-reminder repair and bounded missing-row recovery. No
legacy feature or history was removed. Live known-count drops and quest-screen
acceptance remain to be checked; the older P0 reader matrix below is not superseded
by a UI test count or one successful frame replay.

# Active product checklist — November 2, 2026

Statuses describe evidence, not promises. A test pass is not a live-game acceptance
pass. The latest user direction puts the three core reader tasks ahead of all
other features. Size measurement and dependency work are paused. Under 7 MB remains
an aspirational complete-download goal; no feature removal or hidden extra download.

## P0 — Current tool: acquire once, verify, run the timer

- [x] Reproduce a failed saved frame; 2491/3000 was missed while a neighboring empty
  tool was returned. A scoped recovery now reads the correct tool; this does not
  establish overall accuracy.
- [x] Build a separate persistent Windows OCR engine transport and test its English
  engine availability locally. New frames travel through RAM/pipes, not disk.
- [x] Use positioned OS-recognized words and Place Mode to locate complete numeric
  fields. Text damage may locate a field; it must never manufacture its digits.
- [x] Check the complete number with independent recognition and existing context
  checks; retain the compatibility locator for overlapping labels.
- [ ] Associate tool identity with its current scene/window/scale; invalidate on
  camera movement, overlapping labels, tool swap and window movement.
- [ ] Start the countdown immediately after a verified positional acquisition;
  confirm actual decreasing use on the next bounded acquisition.
- [ ] Preserve the 1.5-second comparison as a scheduled second observation; exclude
  the wait from recognition work and reject ambiguous simultaneous changes.
- [ ] Stop tool scans once active crafting is confirmed. Preserve the countdown
  through covered/minimized game windows; label it an estimate.
- [ ] Preserve Lite Use: initial tool acquisition and optional paired quest
  snapshot, then all OCR stops. No hidden health polling or new capture loop.
- [ ] Reader Debug must show actual input, crop bounds, engine results, rejected
  alternatives, selection reason and stage timings. Unknown is actionable.
- [ ] Compare labeled failed captures, held-out recordings and a live decreasing
  counter. Measure exact value precision, acquisition success and false selections
  separately, plus latency/capture count/process launches. No 100% accuracy claim.

## P0 — Guild quest: scoped progress, both wrapped heights, honest state

- [ ] Locate the guild card before reading numbers; keep Daily/Bonus cards separate.
- [ ] Read the whole counter area including both possible wrapped rows. Cover
  `49/` above `600`, `50/600`, and `101/600` shifted onto the second row.
- [ ] Support cooking and alchemy mission identity, including damaged headings,
  with strong mission context; never borrow a personal quest's matching fraction.
- [ ] Compare independent evidence for the same objective and target. Preserve
  last-seen progress through unreadable/covered frames and scene changes.
- [ ] Keep completed, active, explicitly absent, disabled and unreadable distinct.
- [ ] Preserve confirmed completion and safe new-mission rollover, 95% warning,
  Daily/Bonus tracking and last-seen planner receipts.
- [ ] Keep paired tool/quest acquisition by default. Smart watch stays opt-in;
  Lite Use stops it. Reuse a single capture where possible.
- [ ] Verify Quest Debug input, raw output, boundaries and precise rejection reason.
- [ ] Replay both wrapped heights, completed cards, overlapping objectives, no
  mission and negative frames, then verify installed live progress.

## P0 — No active guild quest alert while crafting

- [x] Add an optional reminder for active cooking/alchemy with no confirmed matching
  mission, shown separately from positive evidence of no active mission.
- [x] Confirm absence only from an explicit readable game statement/state; a hidden
  right-side card is not proof that no mission exists.
- [x] Use existing acquisitions; no additional OCR merely to run this alert.
- [x] If status is unreadable, show a quiet 'quest not verified' action instead of
  an authoritative absent-quest alarm.
- [x] Deduplicate by crafting run and quest status; ten-minute snooze; reset when a new
  matching quest is confirmed. No repeated alarm every timer tick.
- [ ] Completed missions point to claiming/accepting the next quest. Never accept
  quests or send game inputs automatically.
- [ ] Test active matching/mismatching quests, complete, absent, disabled, stale,
  occluded, Lite Use, restarts and changing tools.

## P1 — CP Info, complete in the desktop app

- [x] Existing native calculator, target CP input, market-first exchanges, payback
  model and browser graphs exist. These are the starting point, not a reason to
  call the requested desktop feature set complete.
- [x] Add a clear target selector linked to the existing target calculation.
- [x] Calculate required quantity of **each** supported byproduct from current CP
  and progress %, including complete exchange bundles and leftovers.
- [x] Provide a distinct **Reach my target CP** inverse-planning section: target in,
  exact single-byproduct and mixed-byproduct exchange plans out. The existing
  stock-to-result calculator does not satisfy this request by itself.
- [x] Mixed plans include owned-only feasibility, shortages, bundle-rounded
  quantities, overshoot/leftovers and modeled silver opportunity cost. Explain
  the optimization objective; do not call an unpriced combination most profitable.
- [x] Show owned amount, shortage, resulting CP, EXP to target and silver opportunity
  cost for each route. Never value the same byproducts as both spent and retained.
- [x] Plot one target-progress line per byproduct with visible units and shared
  endpoints; support a text/table equivalent.
- [x] Add a pie breakdown with explicit meaning: owned contribution EXP versus
  remaining target EXP, plus quantities/percentages and an unknown-data state.
- [x] Bring the existing payback comparisons, route simulations, controls,
  graphs and detailed explanations into the desktop workflow.
- [x] Share the existing calculation data/contracts; test browser/native parity and
  retained settings. Keep optional one-shot CP OCR frugal.

## P1 — Imperial, complete in the desktop app

- [x] Browser comparison: buy/craft costs and profit, payout/items per box, sorting,
  mastery and CP allowance, potential daily totals, stock-aware recommendations.
- [x] Advanced disclosure: bounded profit graphs, ingredient quantities/stock,
  expected surplus and return on input cost. Built only when opened.
- [x] Add 'Guru boxes only' checkbox; filter both recommendations and the table.
- [x] Bring those controls, rankings, four recommendations and advanced details
  into the desktop app, with shared calculation/data contracts.
- [x] Preserve exact market IDs, unknown prices, whole-run costs and stock checks
  for the full CP allowance. Reuse caches; no new background market/OCR loops.
- [ ] Clarify potential daily totals versus actual deliveries; verify both
  cooking/alchemy, taxes excluded from delivery, region and saved-state behavior.

## P2 — Previously requested grind/live-window features

- [x] Big Drops, Huge Drops, treasure exceptions and retrospective heat implemented.
- [x] Race Your Best: same-spot best-run pace and projection, comparable price basis,
  excluded pauses/capture gaps; existing median benchmark is only partial.
- [ ] Boss/night timers: regional schedule, day/night countdown, optional alerts.
- [x] OBS browser source for the live grind session; independent opt-in, clock/loot widgets.
- [ ] Twilight reserves and boss sources; draggable widget layout.
- [ ] F9 start/finish and F10 pause/resume; rebind/disable; handle conflicts.
- [ ] Optional first-confirmed-drop session start and conservative spot suggestion.
- [x] Manual pauses and known capture gaps excluded from rates.
- [ ] Optional inactivity pause/resume; distinguish no drops from blocked capture.

## P2 — Workerman and account intelligence

- [x] Integrate optional public Workerman worker-job models into native CP Info
  and the paired browser: exact-ID market prices, CP opportunity cost, break-even
  days, uptime/cost/delay/ramp assumptions and bounded recovery graphs. Require
  full job funding; distinguish existing CP, shortages and unknown prices.
- [x] Keep reference loads explicit, pinned to one revision and weekly cached;
  no extra OCR/polling, no account-data claims or bundled upstream datasets.

- [x] Investigate upstream public Workerman data/source. It contains static item,
  node, house/storage-capacity, worker and production data; no authenticated
  character-account feed has been verified. Do not promise private inventory via it.
- [ ] Document and version a small attributed adapter for useful static metadata:
  worker output origins, production materials, node/CP cost and storage capacity.
- [ ] Verify license/redistribution terms before bundling upstream data/assets.
- [ ] Define reviewed inventory/storage snapshots by character/town, item ID,
  quantity, observed time and completeness; imports never equal captured loot.
- [ ] Add explicit on-demand import/OCR for visible inventory/storage information;
  do not imply that unseen items are known or that absent rows mean zero stock.
- [ ] Track life-skill levels/mastery with source/time and character identity.
- [ ] Add optional HP/stamina snapshots after core readers pass; no continuous HUD
  scan by default and no stale value presented as current health.
- [ ] Asset views: priced/unpriced value, location distribution, useful stock,
  recipe readiness/shortfalls, change history, bars and pies. Avoid double counting
  transfers, owned inventory, worker forecasts and accepted loot.

## P3 — Integration and release acceptance

- [ ] Compact UI consistency/accessibility and recovery walkthrough for each view.
- [ ] Preserve sessions, real history, explicit estimates, exports, Fairy links,
  gear/planner controls, tray restoration and one-shot Lite Use.
- [ ] Run required regressions and isolated packaged checks; obtain live acceptance
  for the three core features before making a reliability claim.
- [ ] Commit source, publish the current default branch/release, preserve previous
  packages and verify a history backup before replacing an installed app.

Dependency order: reliable observations → trusted quest state/alerts → owned account
snapshots → shared economics → comparisons/graphs → optional rewards and overlays.

## Cooking/alchemy workshop · rc.19

- [x] Bounded recursive make/buy routes with deeper variant editing.
- [x] Ordered stage batches, per-batch and total inputs, expected output/surplus.
- [x] Cash versus economic input value, time and profit route comparison.
- [x] Stage-time and purchase-cost graphs, manual milestones and runbook export.
- [x] Real cooking/alchemy chain regressions; preserve ledger/timer separation.
- [ ] Exhaustive external competitor feature-parity audit remains unverified.
- [ ] Core live accuracy acceptance remains required; no 100% OCR claim.

## rc.20 · cooking execution and presentation

- [x] Organic Feed and 20-plus-stage meal planning and explicit next-stage timers.
- [x] Cached chain-wide substitutions, pie charts and teal accent.
- [x] Compact live window, opt-in OBS, silver goals and comparable personal-best pacing.
- [ ] Remaining competitor gaps: see [app audit](GARMOTH-APP-COMPARISON.md).

## rc.21 · layout review

- [x] Compact root shortcuts, grouped workspace navigation, Home default and page preservation.
- [x] Next-stage cooking card, collapsed comparisons/full stage list, guarded primary action.
- [x] CP graph disclosure, grouped Grind settings, retained readers/history/calculators.
- [x] Reuse one visible Grind history calculation and existing pulse bins.

## rc.22 · automatic current craft

- [x] Repeated normal/rare output plus verified tool detects recipe family automatically.
- [x] Captured value/hour, scanned-tool and remaining forecasts, modeled profit ranges.
- [x] Bounded graphs/pies, captured milestones, optional paired-site data.
- [x] Derived activity membership without rewriting accepted loot; blocked-time/Lite guards.
- [ ] Installed live acceptance for this inference feature; no perfect-OCR claim.

## rc.23 - weight and forward production

- [x] Exact extra-ingredient packing from entered maximum/current LT and bag counts.
- [x] Reserve, expected/max-normal-rare output allowance, tool cap and round-down.
- [x] Longest-time, most-crafts and lightest-input category rankings.
- [x] Intermediate recipe load cards and guarded per-load planner timers.
- [x] Bounded downstream consumers, rare root choice and whole-batch routes.
- [x] Ordered queue with kept-output reuse, no double sale/cost and remaining stock.
- [x] Shipped UI and conservation regressions, weight demo and developer contracts.
- [ ] Live validation of carried LT, slot limits and actual yield remains user-owned.

## rc.24 - simple complete production line

- [x] Normalized item/recipe graph with exact variant/substitution relationships.
- [x] Visible full upstream line, branch feed labels and capacity on each step.
- [x] Linked ingredient totals, whole-craft leftovers and selected-load fit checks.
- [x] One-click maximum packing, guarded selected-load timers, compact large chains.
- [x] Exact Sungnyung chain, ratio, graph/cycle and actual shipped input regressions.

## rc.25 - separate starting-stock simulation

- [x] Isolated whole-chain simulation from raw or intermediate starting stock.
- [x] Companion-buy/stock-only modes, single stock pool, leftovers and limits.
- [x] Expected side-output totals, lazy graphs, quantity-first unpriced results/export.
- [x] Separate Planner, Simulator, Imperial and Timers workspaces with timer count.
- [x] No planner/inventory/queue/timer mutations; state-isolation regressions.
- [x] Dedicated sample preview and linked developer documentation.
- [x] Optional complete card grid, expandable dependency sidebar and full-make
  cost/time summary matching the large-meal reference; focused mode preserved.

## rc.26 - map-first product architecture

- [x] Shared exact-ID producer/consumer network across all 990 variants and groups.
- [x] Visible future uses, goal selection and a full connected dependency map.
- [x] Prerequisite-first timeline with stage inputs, quantities and relative times.
- [x] Explicit stage timer/export actions; old packing/economics retained underneath.
- [x] Route/stock isolation, invalid-connection and actual shipped interaction tests.

- [x] Cooking/alchemy default to tool-run limits; independent ingredient/hybrid/manual
  settings, unknown/zero guards and whole-run projections from the selected product.
