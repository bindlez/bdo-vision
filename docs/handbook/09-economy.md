# 09 · Silver, crafting economics and sessions

## Identify before valuing

OCR gives display text, not a market item ID. `market_match.py`, the item catalog and `PriceBook` resolve identities and quote sources. Enhancement, market region and distinct rare variants can change the correct quote. Do not match by a convenient partial word or apply a common elixir's price to its rare counterpart.

An available Central Market quote is preferred. Some unlisted items have separately verified NPC values. `vendor_prices.py` validates identity and parses an NPC quote; cached vendor values remain labeled. Missing prices are excluded from a partial total, not assigned zero while calling the total complete. Keep source, region and freshness visible.

## Recorded value and profit differ

Recorded gross item value is the sum of accepted quantity multiplied by its matched unit value. It is not a confirmed sale. No material costs or fees are deducted from that figure. Crafting Studio can separately model input costs, sale retention, extra expenses, yield and timing to estimate profit. Owned materials can reduce shopping cash while still having economic value; do not equate cash needed with total input cost.

The browser engine `crafting-engine.js` implements planning and recursive material expansion. Its tests cover inventory consumption, yields, cycles, missing quotes, costs, retention, projections and bounded graph series. Preserve warnings about missing prices and recipe cycles when changing the UI. A recursive planner needs a cycle guard even if the current bundled recipes happen to be acyclic.

## Session ranges

An active timer attaches to a particular history identity and event boundary. Only eligible new events after that boundary contribute. Completed receipts must not keep absorbing later drops. `activity_data.timer_earnings` queries scoped event ranges. `grind_session_detail` provides the grind-specific view. The bridge can reject stale history identity with a conflict response, forcing an explicit reattachment rather than mixing profiles.

## Silver per hour

The observed-rate formula is `recorded value / observed seconds × 3600`, with an initial observation requirement before reporting a useful rate. Covered, minimized, unreadable, stale and offline periods are excluded by the observation clock. A readable interval with zero drops still counts; otherwise the rate becomes biased upward.

An optional crafting-only projection can estimate output during certain blocked periods using the existing craft plan. It is separate from confirmed loot and never inserts events into the ledger. It is not applied to grinding. When capture returns, remove the current-gap projection rather than adding the same modeled output on top of real drops.

## Extending the analytics

Define the numerator and denominator first. A useful metric must state its event range, price source, treatment of unknown items and excluded time. Add a pure calculation with hand-checkable examples, then connect it to a bounded summary query and a lightweight display. Avoid reading the whole ledger on every animation tick. A chart should visualize the same verified calculation, not a second independent calculation with different filtering.
