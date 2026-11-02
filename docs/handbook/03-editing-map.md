# 03 · Where to make each change

## Feature map

| You want to change | Start here | Then verify |
| --- | --- | --- |
| Native dashboard, countdown, tool window | [app.py](../../desktop/app.py) | `test_ui_smoke`, `test_tracking_core`, `test_auto_ocr` |
| Big/Huge drops, treasure exceptions, personal rarity and heat | [Big Drops guide](20-big-drops.md), [big_drops.py](../../desktop/big_drops.py) | `test_big_drops`, native smoke and `scripts/test_big_drops.js` |
| Tool discovery and active selection | [tool_reader.py](../../desktop/tool_reader.py) | `test_tool_reader`, `test_tool_status` |
| Tool status wording or estimated durability | [tool_status.py](../../desktop/tool_status.py) | `test_tool_status` |
| Quest extraction and rollover | [guild_quest.py](../../desktop/guild_quest.py) | `test_guild_quest` |
| Quest tab, cadence and alerts | [guild_quest_ui.py](../../desktop/guild_quest_ui.py) | Quest tests plus native UI smoke |
| Tool/quest capture debugging | [ocr_debug.py](../../desktop/ocr_debug.py) | `test_ocr_debug` and real visual check |
| Loot OCR image preparation | [loot_capture.py](../../desktop/loot_capture.py) | `test_reader_efficiency`, `test_extraction_audit` |
| Loot names, quantities and consensus | [item_events.py](../../desktop/item_events.py) | `test_item_events`, `test_text_feed` |
| Deduplication and ledger | [loot_tracker.py](../../desktop/loot_tracker.py) | `test_loot_tracker`, `test_recording` |
| Loot capture controls | [loot_ui.py](../../desktop/loot_ui.py) | `test_loot_toggle`, `test_recording` |
| Silver totals or timer queries | [silver_loot.py](../../desktop/silver_loot.py), [activity_data.py](../../desktop/activity_data.py) | `test_silver_loot`, `test_crafting_studio` |
| Market identity and quotes | [market_match.py](../../desktop/market_match.py), [price_book.py](../../desktop/price_book.py) | `test_market_matching`, `test_price_bridge` |
| Grind sessions and goals | [grind_ui.py](../../desktop/grind_ui.py), [loot_insights.py](../../desktop/loot_insights.py) | `test_grind_tracker`, `test_grind_commands` |
| Browser crafting logic | [crafting-engine.js](../../desktop/assets/crafting-engine.js) | `test_crafting_studio` and shipped inline syntax |
| Equipment recognition | [gear_ocr.py](../../desktop/gear_ocr.py), [gear_sweep.py](../../desktop/gear_sweep.py) | `test_gear` |
| Equipment planner and backups | [gear-planner.js](../../desktop/assets/gear-planner.js), [gear_store.py](../../desktop/gear_store.py) | `test_gear_core.js`, `test_gear` |
| Local API | [planner_bridge.py](../../desktop/planner_bridge.py) | `test_bridge`, `test_bridge_security` |
| Tray and window verification | [windows_bdo.py](../../desktop/windows_bdo.py) | Tray tests and a real Windows check |
| Install/history safety | [storage.py](../../desktop/storage.py), [install_local.py](../../install_local.py) | `test_lite_release` and upgrade rehearsal |
| Packaging | [build_windows.py](../../scripts/build_windows.py), [package_release.py](../../scripts/package_release.py) | Extracted package check and manifests |

## How to follow an unfamiliar behavior

Start at the visible button text and search for it. Find the callback it invokes, then the domain function called by that callback. Locate the nearest regression test by searching for that function or feature. Read both the positive case and the rejection cases. Open the source atlas if you need a symbol index rather than a text search.

For example, an incorrect silver total may originate in a missed loot event, a name that did not resolve to an item, an unavailable quote, or the timer's attachment range. Changing the display formula will not fix a missing event. Trace one event through extraction, consensus, overlap deduplication, ledger insertion, quote matching, query scope and rendering before editing.

## Editing conventions

New modules should have a short module docstring, clear function names and narrow responsibilities. Name elapsed times with units, distinguish a client rectangle from an `(x,y,width,height)` region, and distinguish market identity from display text. Prefer pure functions for rules that should work without BDO. Annotate important boundaries and rejection reasons; do not comment every obvious assignment.

Keep a patch reviewable. A wording change does not need a new algorithm test. A changed OCR acceptance rule does. If you split a controller, move the code unchanged first and verify parity before improving its behavior.
