# 20 · Big Drops, personal rarity and heat

## Ownership and entry points

`desktop/big_drops.py` owns pure classification, the heat function and `BigDropBook`. `desktop/big_drops_ui.py` owns the native trophy room and optional passive reveal. `LootTracker.commit` calls `big_drops.observe` only after accepting and recording a new event and attaching its existing measured session. Cross-panel duplicates return before that hook. Existing history is queried without modifying loot rows or replaying notifications.

The tab is **Big Drops**; the Grind page has a shortcut. The website's Grind page receives `crafting_loot.big_drops` through existing optional sharing. Sharing off exposes no trophy history. `desktop/assets/big-drops.js` and `big-drops.css` are embedded by `python scripts/build_big_drops.py` into the actual planner, with ownership markers. Run the builder after asset edits. `test_big_drops.js` verifies the shipped asset content with platform-normalized line endings and escapes hostile item text.

## Classification

The thresholds apply to an individual unit quote, never a stack total:

| Rule | Result |
| --- | --- |
| Unit quote > 10,000,000,000 | Huge Drop |
| Unit quote > 1,000,000,000 | Big Drop |
| Exactly 1B without a curated exception | Does not qualify |
| Exactly 10B | Big Drop |
| Curated full treasure material/component, including unknown price | Treasure |
| Curated Kabua artifact without a quote | Spotlight, with no invented price |
| Known Crafted / Rare craft observation | Excluded |
| Many cheap units whose stack total exceeds 1B | Excluded |

Prices come from the existing `PriceBook` snapshot, with its source label. No private editable price store, scrape or request loop is added. A later quote can update retrospective tier/value presentation; the display is current recorded item value, not a confirmed sale or an acquisition-time valuation receipt. Treasure status does not require a price. Kabua's Fragment and smaller potion pity materials are deliberately absent from the curated full-drop list. Identical compass/map/telescope/ring names do not prove the specific piece variant, monster or kill source.

The catalog is a conservative editable exception list, not an exhaustive item database. Any accepted item with a qualifying price can enter the value tiers. Add a verified canonical name and source to `CATALOG` for a lower-value non-market exception; do not broaden OCR recognition or guess unidentified item names to make a celebration fire.

`PriceBook.resolve_name` accepts exact curated Treasure names even when a non-market item is absent from the market catalog. Case/typographic-apostrophe normalization is allowed. These exceptions are not added to fuzzy OCR matching, do not create a market ID and do not invent a price. Tests cover real component names, near-miss rejection and HUD noise.

## Sources and comparison boundaries

Catalog context was checked against Pearl Abyss on November 2, 2026:

- [Kabua's Artifact and fragments](https://www.naeu.playblackdesert.com/en-us/News/Detail?countryType=en-us&groupContentNo=6254).
- [Yzrahid / Darkseeker changes](https://blackdesert.pearlabyss.com/tr/en-us/News/Notice/Detail?_boardNo=16818).
- [Treasure families and materials](https://blackdesert.pearlabyss.com/Asia/en-US/Game/Wiki?_masterWikiNo=109).

Those sources establish item context, not a universal numeric rarity ratio. The application stores `global_odds=None` and never treats silver value as drop probability. Market and drop conditions vary. The shelf shows **your observed hours per recorded event**, including zero-drop eligible sessions in its denominator. It requires at least 3 qualified runs, 2 observed hours and 3 recorded events for that item. Eligible locations are curated sources or locations where the item was actually recorded. It uses at most 200 recent completed runs, at least 5 observed minutes per run and at least 80% observed coverage. It does not normalize buffs, kill speeds or party conditions. Comparisons across locations are personal time comparisons, not per-kill or global odds rankings.

## Heat

Heat uses recorded event counts, not item quantities. A large bundle is one observed moment.

For a named current grind spot with at least 80% observed coverage, the personal baseline requires at least 3 prior completed runs, 7,200 observed seconds and 5 qualifying big-drop events. Future runs are excluded from an earlier run's prior baseline. The same current eligible item-price universe is used for current and historical observations.

```text
baseline event rate = prior qualifying events / prior observed seconds
expected events = baseline event rate × current observed seconds
pace ratio = current recorded big-drop events / expected events
heat score = min(100, round(20 × pace ratio))
```

The current run needs at least 300 observed seconds for a pace rating. HOT starts at 2×, ON FIRE at 3×, INFERNO at 5×. These are descriptive product thresholds, not a statistical significance test.

Without the qualified baseline, the label is **Recorded-drop momentum**. Two timed big-drop events inside 15 observed minutes are HOT; three are ON FIRE. The score starts at 30 with 25 additional points per additional recent event, capped at 100. Old clusters cool as observed time advances. A paused capture keeps last measured heat and says so. Retained history with unknown exact observed moment cannot fabricate a burst. Without a measured grind, the journal still celebrates a trophy but withholds measured pace.

The On Fire message is a celebration: **You're on fire. Strike while the iron is hot!** The adjacent note says the next-drop chance is unchanged. Do not describe this as a predictive RNG detector, a luck buff, a drop guarantee or a reason an item is due.

## Persistence, latency and resource budget

Additive table `big_drop_moments(loot_id PRIMARY KEY, session_id, observed_seconds)` stores a deduplicated original measured moment. It references accepted loot IDs, not copied images. An unassigned observation has no invented session time. The existing ledger remains authoritative. Quotes can arrive later: a bounded 32-entry in-memory pending queue retries only when the existing price revision changes and preserves original session/observed time. The queue is not persisted; the retained journal can still rediscover eligible history after restart, with unknown timing where necessary.

The book caches rare-history queries until a qualifying event, session transition, price snapshot change or explicit open. Ordinary cheap drops do not invalidate rare aggregates. The journal shows at most 40 records; totals use SQL aggregation. Baseline lists are bounded to 200 completed sessions; per-item comparison inputs are limited to curated names and recent journal names. Live counts are SQL aggregates, not an unbounded in-memory event list. The view snapshot is reused for a 15-observed-second bucket, unless a meaningful event, availability, session or quote change occurs.

No capture, OCR, price request, animation loop or new periodic service belongs to this feature. Existing Insights refreshes pending classifications and visible views; optional sharing uses its existing update path. Lite Use retains its early return and adds no Big Drop work while idle. Reveals allocate at most one small Tk window and one 6.5-second close callback. On Windows the reveal is hidden until `WS_EX_NOACTIVATE` is applied to its own window; if that style cannot be verified, it stays closed and the journal/status still record the find. It never calls focus/activation on BDO or alters gameplay input.

A local snapshot benchmark on a private SQLite-consistent clone of 8,438 loot rows measured 8.278 ms cold, 3.734 ms median / 4.889 ms p95 warm and 30,689 bytes peak additional traced Python allocation across 25 warm snapshots. The controller normally reuses its result for a 15-observed-second bucket. This measurement excludes Tk, OCR, network, game FPS and whole-process memory; it is not a zero-cost claim.

## Testing and preview

Run `python dev.py test big_drops loot_toggle ui_smoke craft_timer_pipeline`, then `python dev.py check`. Test strict boundaries, missing/nonfinite quotes, treasure overrides, fragments, quantities versus event counts, duplicate IDs, restart, original timing after a delayed quote, zero-drop exposure, coverage/sample guards, burst decay, pending bounds and escaped rendering. The full check includes the real shipped planner and Big Drops renderer ownership/security checks.

Run `python scripts/build_big_drop_demo.py` and open `demo/bdo-vision-big-drops-demo.html`. The standalone preview uses synthetic personal history/prices and a fictional Huge Drop item. It blocks network access with CSP, needs no account/server/library and cannot run native game OCR. Never mix its synthetic averages with production rarity data.
