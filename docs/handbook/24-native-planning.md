# 24 · Target-first CP and native Imperial planning

## CP: target in, exchange plans out

`cp_planner.target_plan` and `engine.targetPlan` use the same CP curve and exchange
data as the existing forward calculator. Target EXP is integrated across brackets;
it is never divided by only today's CP cost. Whole bundles award 900 EXP. They
produce three single-byproduct plans, a feasible owned-only allocation, an owned
mix completed with additional items, and an equal-EXP comparison mix.

Every allocation exposes quantities, bundles, owned stock, shortages, remaining
stock, contribution EXP, result CP and opportunity cost. An unpriced alternative
does not hide CP quantities. Economic optimality is not claimed when prices are
missing. The completed mix identifies a shortage to obtain; it does not assume
byproducts can be bought on the Central Market.

The line graph plots required item quantity against each CP target. Catalyst and
Delicacy coincide because both exchange ten items per bundle; the latter is dashed.
The pie displays owned complete-bundle EXP coverage plus missing EXP, against the
rounded target exchange EXP. It does not mix item counts with silver or treat
partial exchange bundles as immediately redeemable EXP. Graphs have table/text
equivalents, and stop at the modeled 600 CP limit.

`cp-target.js` owns the browser section; `build_cp.py` embeds it before the page.
`cp_target_ui.py` provides native tables, the target selector, per-byproduct lines
and the selected-plan pie. `CPInfo` also exposes native cash/CP/split comparisons,
all reward exchanges, the CP curve, income stress tests, target optimization,
payback-income solver, clickable allocation frontier, sensitivity chart and an
explicit simulation-day recovery slider. None writes projected income to history.

Browser/native parity covers target boundaries and quantities across randomized
states. Native UI tests exercise invalid input clearing, plan selection, frontier
interaction, recovery and solvers. There is no extra OCR, periodic refresh or chart
dependency in this planning layer.

## Imperial: identical rules, native controls

`imperial_planner.py` implements the browser `VisionCraft.imperialRanks` contract
against the same recipe/mastery catalog. Parity tests compare costs, profits,
selected recipes, whole crafting actions and stock decisions across the real
catalog for several mastery/stock states. This is an explicit duplicated-language
contract with shared data and parity evidence, not a claim that Tk executes JS.

`imperial_ui.py` owns the native Imperial tab: Cooking/Alchemy, mastery, shared
current CP, Guru-only filter, four recommendations, cost/profit sorting, quantities,
payout, daily totals, recipe/ingredient breakdowns and lazy advanced profit graphs.
Native current CP shares the CP Info field; it must not use the future target CP.
The browser has the same Guru filter and independent saved browser-origin state.

Buy stock must cover all required meals/elixirs. Craft stock reconsiders recipe
variants/substitutions and verifies each aggregated input quantity. An actual
catalogued NPC purchase can substitute for unavailable market stock, at its NPC
purchase price. A display/source string alone cannot prove NPC availability.
Unknown stock is not zero and never qualifies as stocked. With current CP supplied,
stock and costs are computed for the full daily maximum. The model cannot know
deliveries already used in game and labels daily profits as potential.

Prices come from the existing regional PriceBook using exact item identities. An
explicit refresh reuses the shared 15-minute recipe snapshot cache. No independent
network polling, OCR, automated packing, delivery or transaction is introduced.
Opening a native tab or editing its controls recalculates locally. Closed advanced
graphs do no rendering work.

## Extend and verify

Run `python dev.py test cp_target cp_target_ui imperial_planner imperial_ui`, then
the browser `test_cp_page.js`, `test_imperial.js` and normal project checks.
Regenerate both CP and crafting assets after changing shared sources, then rebuild
the crafting demo so its copied CP block is current too.

Keep live-reader reliability acceptance separate from these deterministic economic
checks. The current prioritized work and remaining account-data constraints are
listed in [Active tasks](../ACTIVE-TASKS.md).
