# Learning to Build a Companion That Knows When to Stop

## A BDO Vision engineering field paper

November 2, 2026 · Living project report · Editable Markdown source

**Narrative disclosure:** The first-person narrator is a fictional learning human,
as requested by the project's owner. This is a literary frame around actual design
notes and scoped test evidence. It does not describe an AI's human experiences,
claim scientific credentials, imply peer review, or turn an experiment into a
production guarantee. No private player history or game captures are included.

## Abstract

I began by thinking a game companion was mainly a matter of reading numbers and
putting them in attractive cards. I learned that the harder problem is preserving
meaning across imperfect observations, timers, prices, recipes, histories and
expectations. A number can be legible and still belong to the wrong tool. A correct
item count can become a misleading profit total if a recipe assumes the wrong yield.
An elegant new launcher can make a working application appear lost.

BDO Vision's response is a local-first architecture with bounded readers, explicit
unknown states, event-driven calculations and recoverable releases. This paper
describes that architecture, concrete failure modes, the move from a small mixed
recipe book to a typed catalog, and the limits of the evidence. The design goal is
low interference with play. This report does not establish zero FPS impact,
negligible total memory on every machine, dependency freedom, or 100% OCR accuracy.

## 1. The product is a chain of claims

I now picture the application as a chain: visible pixels become a proposed reading;
an acceptance policy decides what that reading means; accepted events enter a
ledger; current quotes value items; a recipe model estimates costs; a session or
timer decides which observations belong together; the interface explains the result.

Each link needs its own uncertainty. “I saw this item” differs from “this item has a
market quote,” which differs from “the player sold it,” which differs from “the run
made this much profit.” Collapsing these claims into one silver number makes a
dashboard exciting briefly and untrustworthy later.

The practical rule is simple: do not upgrade evidence while moving it between
features. A projected rare drop is never recorded loot. An inferred batch count is
never verified material consumption. A last-seen quest is never a current quest
counter merely because its card is still visible in the companion.

## 2. Architecture before optimization

The production desktop application uses Python and Tk, Pillow for image work,
Tesseract for recognition, SQLite for history and a loopback HTTP bridge for the
browser platform. A standalone Windows package bundles Python; the checked build
still requires Tesseract English separately. The native reader directory contains
an experiment, not the production replacement.

The browser has dependency-free calculator code, local saved plans and small SVG
graphs. Gear, Fairy, Grind, Big Drops, Crafting and CP share navigation but retain
their domain-specific rules. A public browser demo has no native screen access,
global shortcuts or Windows tray controls. Its prices and drops are explicitly
snapshots or simulations.

This separation lets the native runner remain quiet while someone explores a large
recipe model in a browser. It also creates integration work: item identities,
regions, price timestamps and timer boundaries must survive the bridge intact.

## 3. Read fewer pixels, then do less work

I first imagined optimization as making recognition itself ever faster. The larger
win was often avoiding a recognition request. Useful techniques included narrow
regions, low-priority bounded work, unchanged-image checks, cached quotes and
accepted-state holds. The best reader call is sometimes the call that a valid
countdown makes unnecessary.

The confirmed current-tool pipeline preserves its countdown instead of repeatedly
rediscovering the same tool. Lite Use is more restrictive: obtain the initial tool
durability needed for the timer, then stop the optional readers. A separate manual
read is a deliberate action, not permission to install another standing scan loop.

These are scheduling decisions. Faster algorithms cannot compensate for scanning
the entire screen needlessly, starting several readers together, or rendering a
hidden chart every tick.

## 4. Current-tool detection is an association problem

Several tools can have readable labels at once. The nearest familiar name is not
necessarily the active tool. A camera can move; an empty tool can remain nearby;
another label can be more legible than the one that matters.

The Place Mode control is a useful contextual anchor. Geometry narrows the candidate
labels around it. A second capture roughly 1.5 seconds later can provide stronger
evidence when the same field's durability decreases. Anchor placement gives a
fast provisional association; a valid decrease confirms use under the existing
timing and context rules.

The two signals answer different questions. Geometry asks which label belongs to
the relevant area. A temporal comparison asks whether that tool is being consumed.
Neither alone is a universal proof. Hidden labels, camera movement between frames,
multiple changing candidates and interrupted crafting still require rejection or
another explicit acquisition.

## 5. Cached digit boxes can become a trap

One saved failure made the lesson concrete: a field could change from 2492 to 2491,
yet stale per-digit geometry could produce 241. Reusing yesterday's box was cheap,
but the cheap result had lost a character.

The revised reader can use digit geometry to acquire a field, then discard that
geometry after success and read the whole numeric pair on later changes. A fresh
bar-fill measurement supplies an independent consistency check. The bar is not a
license to reconstruct missing digits; a literal pair still has to be read.

Near zero, another failure could replace a nearly exhausted tool with a large
nearby number. The countdown's identity and lifecycle matter as much as numeric
plausibility. A reset requires credible new-tool evidence rather than any number
that resembles a valid capacity.

## 6. Two agreeing passes are useful, not magical

Two OCR transforms can agree on the same wrong text. Their errors are correlated:
they share the image, font, occlusion and much of the preprocessing. Agreement is
one acceptance condition, not a mathematical guarantee of correctness.

Better evidence combines independent constraints: a literal current/capacity pair,
plausible capacity, fresh bar geometry, consistent context, expected capture timing,
and a coherent decrease. The reader preserves unknown when these constraints do
not agree. Accuracy is measured on accepted and rejected cases, not only on a few
attractive successful screenshots.

## 7. Wrapped quests taught me to distrust visual indentation

A guild objective can place its numerator on one line and its denominator on the
next, then wrap differently when the numerator gains a digit. A heading's left edge
need not be the counter's left edge. Cropping beneath the heading can remove a
leading digit while leaving perfectly readable remaining text.

The focused quest reader starts from gold heading cards but reads the full widget
width beneath them. It bounds the body at the next heading and compares both the
normalized objective and its counter across focused passes. Matching numbers on
different objectives are insufficient.

Guild, Daily and Bonus scopes remain distinct. Completion requires actual completion
evidence within the relevant scope. A completed Daily objective must not complete
the guild mission. A last-seen snapshot can be shared with a craft timer without
inventing an estimate between reads.

## 8. Scheduling states are part of accuracy

“Waiting for paired tool scan” sounded reassuring even when quest tracking was off
or the tool timer was deliberately holding recognition. The application needed
states that described the actual pipeline: off, ready, queued, reading, verified,
partial, retry, confirming and blocked.

A bounded queue is useful when another reader is briefly busy. An unbounded retry
loop is a hidden performance bug. Optional Smart quest watch is distinct from the
default paired snapshot and remains off unless selected. Lite mode cancels optional
work rather than leaving a confusing callback alive behind the scenes.

## 9. Debugging should show the same evidence the decision used

Raw OCR text alone cannot explain a missing leading digit. A crop preview, accepted
candidate, rejected alternatives, timing, geometry and reason codes help a developer
see whether failure began in capture, cropping, text recognition or interpretation.

The project reused the loot reader's debugging pattern for tool and quest readers.
This is valuable product functionality: the player can understand why a reading is
waiting without correcting every item manually. Diagnostics must remain bounded
and private. Publishing a debug page is different from publishing someone's desktop.

## 10. A ledger is more durable than a screen

Notifications disappear. A ledger gives accepted events stable identities and
session boundaries. Repeated scans must not multiply the same notification, while
a later identical drop must still be allowed to create a new event.

This tension makes deduplication domain-specific. A universal rule such as “ignore
the same item for ten seconds” can suppress legitimate repeats. Comparing every
frame without state can double-count lingering notifications. Capture timing,
ordered rows and notification transitions provide better context than item names
alone.

The public evidence here does not establish a zero-miss loot rate. A production
accuracy study would need labeled runs, repeated drops, occlusions, different UI
scales, rare items, empty frames and an independent ground truth.

## 11. Capture gaps belong in rates

Silver per hour is meaningless without its denominator. A blocked window can stop
observation while the player continues crafting or grinding. Treating all wall-clock
time as observed time understates the observed rate; extrapolating missed loot
silently overstates recorded totals.

Vision preserves observed and paused time. Optional crafting projections require a
current connected blocked state and explicit consent. They stop at the timer's end,
reset when capture returns and never enter the accepted-event ledger. Rare extras
are not invented during a gap.

This design cannot recover unknowable events. It can explain exactly what the
visible rate covers and what the forecast assumes.

## 12. Prices are structured evidence

An item name is not always a unique market identity. Event items and normal items
can share names; equipment has enhancement variants; regions have different quotes.
The recipe planner therefore uses exact item IDs and base variants, and the shared
cache keeps the selected region explicit.

Arsha's base price, last sold price and current stock are different fields. A base
quote is not an executable sell offer. A fetched timestamp differs from a provider's
underlying update time. A stack of 750,000 items may take much longer to sell than a
calculator's arithmetic suggests.

For example, a checked NA Clear Liquid Reagent response reported a 9,850 base quote
and a 9,900 last sale. A player's 12,000 observation was a reason to refresh and
inspect the quote basis, not a reason to hardcode either number.

## 13. Recipes became shared infrastructure

The old 114-entry recipe book mixed genuine names with placeholder group labels,
static fallback prices and incorrect ingredient combinations. That affects far more
than the recipe page: it distorts shopping, profit, session costs and CP tradeoffs.

The normalized public catalog contains 990 distinct variants: 152 cooking, 92
alchemy, 424 non-imperial processing and 322 imperial packing entries. There are
105 substitution groups with replacement values. Existing compatible IDs remain
available so old plans can still resolve.

The important unit is a recipe key, not just an output name. Several methods can
produce the same item. A native session must keep the selected recipe identity and
resolved substitutions when it freezes its cost model.

## 14. Substitutions are arithmetic, not synonyms

A group ingredient has a required value. A selected substitute supplies some value
per item. Required units per craft are the ceiling of required value divided by
substitution value. Rounding after multiplying all crafts can incorrectly assume
fractions can be shared between separate craft actions.

Cheapest quoted substitution compares the resulting whole-item cost per craft. It
does not pick the lowest displayed unit price blindly. Inventory and make/buy
choices must refer to the selected concrete item, not an abstract “Blood 2” bucket.

Optional rare-intermediate equivalence is a model with an explicit assumption. It
must not become a fabricated inventory count or imply that every ingredient accepts
the same replacement rule without checking the game.

## 15. Shared inventory exposed a double-counting bug

Recursive planning needs both a material tree and a stock ledger. If one intermediate
batch makes more than the current target needs, the excess can serve a later plan.
Charging its market value again would count a cost already charged when producing
the batch.

The planner allocates owned stock once across queue order and separately marks
newly produced intermediate excess. Full intermediate batches are charged when made;
their modeled surplus is reused without another charge. Original owned inputs still
have an economic opportunity cost even when shopping cash is zero.

Cycles and runaway recursion are bounded. A cycle falls back to buying with an
explanation; exceeding the depth/node budget leaves the result incomplete. A plan
limit should never quietly turn required materials into zero cost.

## 16. Expected production is a model

The calculator uses dated mastery brackets and recipe output ranges to model normal
and rare yields. Cooking mass-production chance changes expected speed; eligible
processing uses its batch model and chosen success assumption. User overrides are
visible and can be reset to the mastery model.

These outputs are expectations over repetitions. They are not guaranteed results
for one batch. Missing processing rare chances are excluded rather than guessed.
The source catalog does not provide every minimum skill requirement, so eligibility
remains a visible limitation and a link to game-item details.

Alchemy extra-item distributions are optional, require their own prices, and remain
probabilities. An extremely small expected quantity of an expensive rare item is
not cash in the player's warehouse.

## 17. CP is an opportunity-cost problem

Directly selling byproducts to an NPC can be legal arithmetic and a poor primary
comparison. The meaningful alternative is often exchanging them for marketable
materials. The CP planner now uses the best available priced material exchange by
default, with direct NPC selling available separately.

Every whole exchange batch can serve CP or a material reward, not both. Leftovers
remain in inventory in market mode. Missing market prices keep cash opportunity and
payoff unknown. Missing alternative rewards can still change which known option is
best, even if one priced route is available.

CP advancement walks the actual changing cost curve. It does not divide all gained
EXP by the current level's cost. In the example model, 750,000 catalysts at 490 CP
and 19.26% provide 67.5 million CP EXP and reach 567 CP plus approximately 95.86%.
The model stops at 600; it does not claim that 600 is a game hard cap.

## 18. Payback needs a job for the new CP

I learned to ask what additional net income the new CP will unlock. Existing income
is not a benefit created by this decision. Undeployed CP has no recurring silver
return merely because it increases a displayed total.

The model distinguishes per-CP income from whole-project income, deployed capacity,
uptime, setup cost, delay and a linear ramp. Cumulative productive days during ramp
are quadratic; after ramp they are linear. Break-even solves cumulative incremental
income equals foregone material-exchange value plus setup cost.

The interface offers deadline income requirements, cautious/base/strong scenarios,
reserve-constrained whole-CP targets and cash-versus-income graphs. These are
decision aids. Worker jobs, actual node bottlenecks, market changes and future
byproduct generation are not automatically proven by the simulation.

## 19. Tax is a collection model

The Central Market's base collection is 65%. A Value Pack's 30% collection bonus
makes 84.5%, rather than subtracting thirty percentage points from tax. The helper
applies collection bonuses to that 65% base and lets the player enter effective
retention directly when special circumstances apply.

NPC ingredient purchase prices are labeled purchase assumptions, not substitutes
for material-exchange selling value. Imperial delivery uses a separate untaxed
return model; daily limits and delivery availability still need in-game checks.

## 20. Liquidity deserves its own label

A market-wide fourteen-day volume divided by fourteen is an average, not today's
sales and not a promise that my listing will sell. Stock, last sale and average
volume should never share one ambiguous “activity” label.

The optional opportunity scan streams a public market response and retains recipe
identities only. It runs on demand and uses a cache rather than an ongoing polling
service. The default selected-plan quote lookup remains narrow. The offline demo
uses a dated compact snapshot; it does not make background requests to seem alive.

## 21. Dopamine can reward clarity

I want a satisfying product without teaching the player false causality. Material
readiness, captured-output goals, completed plans and verified big drops can produce
useful progress feedback. A simulated recovery milestone must look and read like a
simulation. A hot streak does not improve the probability of the next independent
drop.

The interface keeps quantity and useful results close together, then progressively
reveals assumptions, market detail, production order and graphs. Small SVG charts
need no chart runtime or animation loop. Unknown states use words as well as color.

The best reward is often understanding what to do next: buy the missing ingredient,
refresh a quote, give the new CP a job, or let an already valid timer run quietly.

## 22. Simplification is not deleting half the product

An AST inventory found no exact duplicated Python function bodies. That does not mean
the codebase was simple. Duplicate economics in different UI surfaces and manually
synchronized embedded assets were more important sources of inconsistency.

The cleanup replaced an independent quick profit calculation with the shared Studio
model and established deterministic ownership for crafting assets and recipe data.
The legacy research summary now delegates its economics to the same engine.

Native/offline CP implementations remain intentionally separate and parity-tested.
Generated delivery copies remain generated. Reader-specific acceptance rules stay
separate where their evidence differs. Removing those distinctions to make a line
count smaller would make the system harder to understand.

## 23. A release is also a data-safety protocol

A source launcher that searched for Python made one update fail on a machine whose
earlier standalone package worked. The correction was to restore a stable standalone
executable path and verify the package without relying on Python in the system PATH.

Updates use a consistent history backup, an instance lock, immutable version folders,
archive hashes and before/after database verification. A checked executable is not
replaced while it is running. Previous release folders are recovery tools, not clutter
to delete during an optimization pass.

Local commits, immutable checkpoints and exact remote tree backups answer different
questions. A local Git commit proves what was reviewed; a package manifest identifies
what was shipped; a remote backup protects source recovery; an extracted executable
check catches packaging problems that source tests cannot.

## 24. What the measurements do and do not show

The preceding CP/tool/quest checkpoint passed 370 Python tests plus shipped-page,
security, JavaScript and handbook checks. Its extracted Windows package passed the
native-widget, bridge, history-integrity and synthetic-OCR checks. Later calculator
work added further tests; exact current counts belong to the release's check report.

In a private saved-pair replay, initial tool acquisition used six OCR calls and about
1.019 seconds; the subsequent changed-field read used four calls and about 0.494
seconds. A focused quest replay took about 1.091 seconds compared with about 1.977
seconds for the earlier broad path. These are individual saved-scene measurements,
not a device-independent benchmark or population accuracy study.

A warm CP target analysis measured a median near 0.587 ms and p95 near 0.983 ms over
25 calls, with about 12,964 bytes of peak additional traced allocation in that scoped
Python test. A later Node run of 1,000 selected recipe plans took about 9–10 ms in
aggregate. Those figures exclude rendering, network requests, OCR, total process
memory and FPS. No statistical confidence interval or game performance guarantee
is inferred from them.

## 25. Validation should cross the feature boundaries

The regression suite exercises literal OCR rejection, changing-digit geometry,
wrapped quest cards, timer holds, Lite scheduling, session boundaries, price identity,
origin guards, shared inventory, recipe cycles, unknown prices and history handling.
Python and JavaScript CP calculations are checked for numeric parity.

The actual shipped inline page is syntax-checked; owned asset equality checks prevent
editing an unused source copy. Small DOM fixtures test interactions. These are not a
substitute for visual browser inspection or live play on different display scales.
Packaging checks run the extracted Windows executable with a disposable profile.

When desktop control reports active input or unreliable focus, that is a validation
limit, not permission to send blind clicks. The checked ZIP can remain reviewable
while a safe installed-app restart waits for the player.

## 26. The next experiments I would trust

- A labeled accuracy corpus with independent counts, UI scales, repeated drops and
  occlusion scenarios; report false acceptances separately from missed reads.
- End-to-end CPU, working-set, allocation and game-frame-time measurements on stated
  hardware, with tracking off, initial acquisition, confirmed timer hold and grinding.
- Controlled recipe-yield samples by skill/mastery, rather than silently treating a
  public planning formula as an observed distribution.
- A native BDO-specific recognition experiment compared against the same labeled
  scenes before replacing the established production reader.
- Automated consistency checks for data-source changes, recipe identities and CP
  exchange rewards after game patches.

I would accept a smaller honest result over a spectacular unexplained percentage.
The engineering habit I learned is to stop work when the evidence is sufficient,
stop readers when the product no longer needs them, and stop the interface from
claiming more than the data can support.

## Sources and reproducibility

- [Project source and developer handbook](https://github.com/bindlez/bdo-vision/tree/gear-planner): production modules, tests, builders and editable documentation.
- [BDolytics crafting reference](https://bdolytics.com/en/crafting?category=alchemy): public calculator controls and factual recipe/model data; original Vision implementation.
- [Public recipe data](https://bdolytics.com/api/trpc/calculator.getCraftingRecipes), [material groups](https://bdolytics.com/api/trpc/calculator.getMaterialGroups), [cooking mastery](https://bdolytics.com/api/trpc/calculator.getMasteryCooking), [alchemy mastery](https://bdolytics.com/api/trpc/calculator.getMasteryAlchemy), [processing mastery](https://bdolytics.com/api/trpc/calculator.getMasteryProcessing): checked November 2, 2026; response hashes recorded in the catalog provenance file.
- [Arsha API](https://api.arsha.io/): public regional market quotes; exact price basis and timestamps remain part of each snapshot.
- [Official Central Market guide](https://blackdesert.pearlabyss.com/Asia/en-US/Game/Wiki?_masterWikiNo=39): base collection and Value Pack explanation.
- [Mysterious Catalyst](https://bdocodex.com/us/item/9781/), [Witch's Delicacy](https://bdocodex.com/us/item/9780/), [Blush Leaf](https://bdocodex.com/us/item/9795/): exchange references.

Reproduce checks from a development checkout with `python dev.py doctor`,
`python dev.py check`, `node scripts/test_crafting.js`, and the documented Windows
package check. Use a disposable profile. Catalog import accepts public response
snapshots and records hashes; it does not read a player's profile. This paper is a
living engineering report and should be revised when the evidence or product changes.
