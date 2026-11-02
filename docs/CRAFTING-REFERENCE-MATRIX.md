# Crafting reference and implementation matrix

Checked November 2, 2026. Reference: [BDolytics Crafting](https://bdolytics.com/en/crafting?category=alchemy), its publicly served list/detail controls and public game-data calculator responses. The site is a client-rendered application: the text-only web view has no readable page body. Public data/control inspection establishes the rows below; it is not an assertion that every authenticated workflow was exercised. Vision uses original calculator code and presentation.

## Catalog evidence

990 distinct recipe keys: 152 cooking, 92 alchemy, 424 non-imperial processing and 322 imperial packing variants. 105 material groups carry explicit replacement values. All ingredient, ordinary-output and rare-output IDs resolve in the imported metadata. Two additional farming exchange identities support CP. Normalized sources and response hashes are in `desktop/assets/crafting-provenance.json`.

The previous 114-entry book contained real recipe names, placeholders such as “Blood 2,” static fallback prices and incorrect ingredient lists. For example, the old Demihuman Hunt entry used Oil of Storms; the current public recipe instead specifies a blood substitution group, Powder of Flame, Birch Sap and Pure Powder Reagent. Existing compatible recipe IDs are retained for saved plans.

## Feature map

| Public reference capability | Vision implementation / limit |
| --- | --- |
| Cooking, alchemy, processing, imperial categories | All 990 variants; processing method filter includes imperial packing |
| Search by recipe / ingredient, favorites | Indexed bounded recipe browser; local saved recipes |
| Recipe variants | Exact recipe-key selection, including intermediate variants |
| Substitution groups and replacement values | Concrete ingredient selection; whole units rounded per craft; cheapest quoted choice action |
| Quantity / crafts / output goals | Batches and target-main-output controls |
| Mastery assumptions | Dated cooking/alchemy/processing tables, bracket display and saved activity settings |
| Normal / rare yields | Expected-value model and explicit overrides; unknown processing rare chance is excluded |
| Mass cooking / processing and success rate | Optional model with timing assumptions shown; not a guarantee of action duration |
| Recursive recipe tree and buy/make | Bounded production order, cycles rejected into buy steps, maximum depth 12 / 400 material nodes |
| Storage and shopping shortages | Owned quantities; one allocation across queue; intermediate excess carried forward |
| Market prices and NPC ingredients | Shared Central Market cache by exact IDs; NPC purchases labeled; no sample-price fallback |
| Value Pack, ring, family fame, sale tax | Retention helper and editable retention assumption; no duplicate item-price editor |
| Keep an output | Main / rare keep toggles exclude kept output from sale proceeds |
| Byproduct use | Kept by default; optional material exchange value, mutually exclusive with CP |
| Alchemy mastery extras | Tier probabilities and optional weighted distribution valuation; incomplete extra-item prices keep profit unknown |
| Profit, inputs, retained value, hourly/time/EXP/weight analysis | Shared expected model, signed profit graphs and sale-value sensitivity |
| Imperial returns | Untaxed modeled base return + mastery bonus; eligibility, daily limits and delivery availability remain in-game checks |
| Saved multi-target plans | Local production queue, shared stock allocation and shopping export; no account/cloud synchronization |
| Price / profit and market-volume list ranking | Cached net-profit / EXP ranking and minimum-profit filters. Optional streamed public market snapshot supplies 14-day daily-average volume filters; stock and last sale remain distinct |
| Custom item-price overrides | Deliberately omitted per the user's request to reuse Central Market prices |
| Skill and weight constraints | Output weight shown; absent minimum-skill facts stay absent. The linked game-item details support manual eligibility checks |
| Analytics | Expected progress, cost/proceeds breakdown, sensitivity, CP cash/payoff/target graphs |
| Timer | Existing native tool countdown plus optional browser plan timers; planned costs locked when started |
| Extra platform integrations | Loot/session economics, Guild last-seen receipts, CP opportunity costs, Big Drops, Gear and Fairy navigation preserved |

## Pricing meanings

Live requests use Arsha's public `GetWorldMarketSubList` responses. `basePrice`, last sold price, stock, region and fetched time are distinct. Base price is a reference quote, not the cheapest listing, an executable offer, a forecast or a confirmed sale. Cached requests have a five-minute TTL. The calculator adds no standing market refresh loop and no OCR workload.

On November 2 the sampled NA Clear Liquid Reagent base quote was 9,850 and its last sold price 9,900; the user's 12,000 observation may refer to another time or quote. The input observation was not hardcoded. Offline previews use a clearly dated snapshot and cannot refresh live data.

Market-first CP compares the material rewards obtainable from a whole exchange batch, after the chosen sale deduction. Direct NPC selling is optional. Unexchanged leftovers stay in inventory. With no priced market reward for an owned byproduct, cash opportunity/payoff are unavailable rather than zero. Missing alternatives can still change which priced route is best.

## Boundaries

This matrix is intentionally narrower than “every feature is identical.” Private account/cloud flows are not copied, custom item-price overrides conflict with the user's preference, and missing skill facts and unavailable volume values are not invented. Public factual data is attributed; no reference-site UI, branding, component implementation or private endpoint is shipped.
