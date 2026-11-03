# 25 · Workerman and CP payback

## What the integration knows

The optional Workerman panel in native CP Info and the paired browser planner
models **one additional worker production job**. The public project is a static
reference, not a personal-account API. It cannot read a player's workers, storage,
inventory, available lodging, life skills, HP or stamina. Existing account-import
tasks remain separate. This feature neither captures the game nor records loot.

Public sources:

- [Workerman application](https://shrddr.github.io/workerman/)
- [Repository](https://github.com/shrddr/workermanjs)
- [Yield observations](https://github.com/shrddr/workermanjs/blob/main/data/manual/plantzone_drops.json)
- [Production and travel formulas](https://github.com/shrddr/workermanjs/blob/main/src/stores/user.js)

The initial live adapter check resolved revision
`4d5a392ab43c56eb09da78a4d982260ab3be3fee` and 324 supported production jobs.
This is a verified reference load, not evidence that those yields are guaranteed
in game or that every possible job is supported. The panel shows the revision,
fetch date, yield sample count and output price dates. Fetch date is not the date
of the upstream observations. Upstream code/assets/full data are not bundled;
redistribution permission has not been established.

## Ownership and data flow

- `desktop/workerman.py`: fixed public source adapter, graph routes, normalizer,
  exact-ID quote join and pure discrete-job forecast.
- `desktop/cp_workerman_ui.py`: collapsed native controls and bounded Canvas graph.
- `desktop/assets/cp-workerman.js`: collapsed browser controls and bounded SVG.
- `desktop/planner_bridge.py`: protected same-origin `POST /workerman` with
  `reference` and `model` actions. A file preview explains that it needs the
  paired app; it cannot call the protected bridge from an opaque file origin.
- `scripts/build_cp.py`: embeds the browser asset into the planner and preview.

Nothing fetches at startup. A user-requested reference load resolves the public
GitHub main ref, validates its 40-character SHA, then fetches six allowlisted JSON
files from that **same revision**. Responses have individual byte limits and
12-second request timeouts. Only normalized facts are cached in the app profile
as `workerman-reference.json`. A seven-day cache and per-path lock prevent repeated
downloads. Failed refreshes preserve the old cache. No credentials, captures,
local inventory or personal worker plans are sent upstream. The optional reference
cache is not packaged with a release. Public data isn't treated as instructions.

## Route and output model

For each supported production node, the normalizer considers public worker-NPC
base towns with reachable travel distances. Dijkstra minimizes the sum of node
connection CP from each town; ties use travel distance. The displayed route is
the cheapest full route in this model, **not** the player's incremental route,
the shortest walking route or an optimal empire. Housing, prerequisites not
represented in the public graph, and shared existing connections need review.

The editable **additional CP needed** is the actual investment constraint. Include
extra lodging CP there; subtract connections already owned. If that number is
zero, the job can run without turning byproducts into more CP and its income must
not be credited to the turn-in.

With `p = productivity_percent / 100`:

```
work chunks = ceil(base workload × (2 − p) / worker work speed)
cycle minutes = 10 × work chunks + 2 × travel distance / move speed / 60
cycles / full day = 1440 / cycle minutes
output / full day = cycles / full day × observed regular yield
gross / full day = sum(output × exact-ID market unit price)
net / modeled day = (gross × sale retention − declared full-day costs) × uptime
```

Defaults (150 work speed, 7.5 move speed, 0% productivity) are editable assumptions,
not the user's stats. Giant yield observations are optional. Luck drops and worker
skills are excluded. Refeeding and stamina aren't simulated; uptime must account
for downtime. Declared running costs default to zero and must be filled in to
include feeding. Output is fractional expected yield, never a guaranteed count.

Prices reuse the existing regional PriceBook/recipe market cache. Unknown outputs,
conflicting ID aliases and vendor-only quotes stay unpriced. A missing material
price never becomes zero. Refreshing the shared recipe snapshot is explicit and
does not promise market coverage for every Workerman output. Cached market prices
are valuation estimates, not immediate guaranteed sales.

## CP investment and break-even

The target-first CP engine supplies its owned mix plus required additional
byproducts (`target_plan(report)['completion']`). Its silver opportunity cost is
the market exchange value of the complete byproduct allocation. Setup cost is
added once. Missing byproducts are shown, not assumed owned or market-buyable;
payback for such a plan is explicitly hypothetical.

The job produces incremental income only if the target unlocks at least its entire
additional-CP requirement. Partial funding never earns fractional-job income. A
button sets current CP + required CP as the minimum target, within the supported
600 CP curve. Extra target CP stays unassigned with no additional income.

```
investment = target byproduct opportunity cost + one-time setup
payback: net/day × productive_days(day, delay, ramp) = investment
day-N advantage versus cash = modeled income to N − investment
```

`cp_forecast.payback_days` solves the existing exact delay/ramp integral. There is
no payback when price/cost is unknown, a whole job cannot fit, existing CP alone
can fund it, or modeled net income is nonpositive. The existing free-form income
scenario is kept separate; the discrete model never silently replaces it with a
linear per-CP estimate. No forecast is written to silver history.

Both charts show a 25-point cumulative-income line and the investment line.
They update on user actions only. Native controls recompute locally; the browser
sends a bounded same-origin model request only on Calculate. Editing a scenario
clears the prior browser result, including a result returned after the edit.

## Validation and extending

`tests/test_workerman.py` checks travel/work arithmetic, graph CP, pinned requests,
weekly reuse, failed-refresh preservation, ID conflicts, shortages, zero uptime,
negative net, discrete funding and existing-CP exclusions. The native CP test
exercises the actual controls and minimum-target action. Bridge tests check
same-origin enforcement, request limits, cached model execution and invalid nodes.
`scripts/test_cp_workerman.js` executes the real browser actions, target selection,
payback SVG, stale-result clearing and offline message without real network calls.

Future multi-job plans must aggregate shared connection CP and lodging before
ranking. Never add independent full-route costs or use all existing worker income
to repay new CP. Keep actual owned-account snapshots separate from reference facts
and forecasts, and retain the no-background-OCR contract.
