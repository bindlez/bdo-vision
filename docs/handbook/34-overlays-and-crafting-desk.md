# 34 · Overlays and the crafting desk

## Product ownership

The website is the primary calculation/planning surface. The launcher retains
capture, the current tool timer, alerts, tray restoration and every original
workspace page. Native CP and Imperial are retained compatibility views. New
planning functionality belongs on the website, with launcher shortcuts rather
than a second model. See the [ordered product brief](../UX-RELEASE-PLAN.md).

`WorkspaceNavigation` exposes Home/Craft/Grind/Quests/Planning/History/Readers
buttons with a visible second row of destinations. It does not use destination
menus. `locations` still covers every notebook page; opening a group does not
change the selected page. External shortcuts select the appropriate nearby
actions. Explicit website shortcuts use the paired loopback bridge, including
`#cp` and `#imperial`; no fixed port is assumed.

## Crafting desk

The searchable recipe list stays visible by default. rc.27 migrates the previous
map-wide default once, preserving goals, quantities, run rules and saved plans.
The user can still explicitly expand the map or the packing overview.

`crafting-studio.js` transforms **owned** essential disclosure markup into permanent
sections with stable IDs and headings. `craftStudioDeskMarkup` tracks nested
details so optional inner choices remain intact. Overview, ingredients, packing,
map/timeline, production steps, output, cost/tax, graphs, character and queue have
direct keyboard-accessible anchor buttons. They scroll/focus without recalculating
or mutating plans. The header's economics describe the selected recipe; the map
continues to label whole-line totals separately. Manual timers remain explicit.

The live context strip is separate from the recipe model. `/durability` carries a
small `companion` timer snapshot and `guild_status` using its existing poll. The
original signal/timer receipt fields remain compatible. Full loot details are
still optional; this new context never enables them. The strip distinguishes a
countdown estimate, observed capture, unavailable sharing, last-seen quest and
current verified completion. Disconnects remove current-status claims. A new
bridge packet never makes a stale OCR reading fresh. Buttons open CP, Imperial or
the native capture controls; background packets never navigate or steal focus.

## Native overlay modules

| Module | Responsibility |
| --- | --- |
| `overlay_layout.py` | Pure preference validation, screen bounds, docking, snapping, reveal tiling, bounded queue |
| `game_overlay.py` | Tk chrome, our own Win32 styles, monitor work area and drag feedback |
| `live_hud.py` | Compact live metrics and Overlay settings |
| `drop_reveal.py` | One passive Big/Huge/Treasure reveal, dismissal, snooze and event-only animation |
| `live_grind.py` | Existing session payload/cache and opt-in OBS sharing |

Open **Grind → Open game overlay**. Drag its header; near an edge the frame turns
teal and labels the release destination. Release clamps/snaps and saves the
position. Settings offer four corner buttons and two sizes. Positions respect
taskbars, negative desktop coordinates and the monitor containing the overlay;
reopening clamps removed/offscreen positions. Reveals try below, above, left,
right and screen corners, choosing minimal HUD overlap. Tiny monitors may lack
enough space; no claim is made that all BDO HUD components are auto-detected.

`WS_EX_NOACTIVATE` and `WS_EX_TOOLWINDOW` apply only to our own new windows before
they are shown. Failure to verify passive style closes the surface. No BDO hooks,
injection, focus calls or global keyboard listeners are added. Lock adds
click-through to the dashboard; recover it from the launcher’s always-visible
Overlay settings. Reveals remain dismissible. Windowed/borderless BDO is advised;
exclusive fullscreen visibility and mixed-DPI arrangements need live acceptance.

## Reveals and resource limits

Accepted ledger events alone enter the journal. The UI has one reveal plus four
pending events; IDs are deduplicated across a bounded 64-ID window. Pending UI
events expire after 25 seconds. Overflow/expiration affects presentation only;
the recorded journal is unchanged. Default lifetime is 7 seconds; 10/14 are
options. No queued UI or animation survives shutdown. Snooze mutes reveals for
10 minutes without stopping recording. Sound is opt-in and off by default.

Motion is a 250 ms gem entrance (32 ms callbacks), followed by a 200 ms dismissal
rail update only while a reveal exists. Reduced motion skips the entrance. There
is no idle animation, capture, network poll or extra price lookup. The HUD reuses
the existing one-second tick; unchanged display data avoids widget writes and
session aggregation remains cached by ledger/price/session identity.

Preview buttons pass synthetic events directly to presentation. They never call
`observe`, write loot, attach a session or award a real trophy. The offline
[browser playground](../../demo/bdo-vision-overlay-demo.html) and
`python scripts/preview_overlay.py` are sample-only. `--framed` gives the same
native widgets normal review chrome for accessibility inspection; it is never a
production overlay mode. That review exits after one minute.

## Quest reminder repair

The existing one-second Insights tick checks **state**, not pixels, when crafting
starts or a new quest decision becomes available. A fresh completed mission now
offers an audible next-quest reminder, subject to the existing sound setting.
Completion and reminder in one pass share a two-second sound gate. Snooze and
per-session decision deduplication remain. Hidden/stale/unknown cards stay
unverified; only the already-verified explicit absence message says no active
mission. The reminder is included in the website status strip. Lite Use adds no
reader or image work.

## Incomplete personal-loot recovery

`loot_positioned.py` is a bounded fallback for a chat read with missing row
consensus. It reuses the existing Windows OCR worker; no new process or capture
loop is created. Lock acquisition has a 10 ms budget, two image variants have
one-second response deadlines, and busy/unavailable recovery retains the original
Tesseract consensus. Inputs stay within the existing 1.5-million-pixel worker
budget. Exact unchanged-feed caching is preserved.

OS word line IDs can put an item before its receipt prefix. Recovery groups words
by their physical row and sorts by x. Receipt-prefix diacritics and the observed
`have7obtained` / `have.obtained` separators normalize **only before `[`**. Item
spelling and quantity digits are never rewritten by this normalization. Both
physical rows must parse the same personal receipt and resolve to a known item.
Different row counts, contradictory quantities, unknown names and disagreements
stay holes. Recovery must add events without contradicting the old consensus.

A private saved eight-message frame replay improved from five accepted messages
to all eight exact names/counts in order, taking 0.75 seconds in one local run.
This is one frame, not a live recall/FPS claim. Public tests contain synthetic
word geometry and receipt strings only. Loot sharing now exposes small reader
health fields: last capture/save, scan duration/gap, holes, unmatched names and
uncertain overlap. None of these convert missing items into silver.

Run `python dev.py test game_overlay loot_positioned guild_reminder bridge
workspace_navigation text_feed item_events structured_reader`, then the full
`python dev.py check`. Live acceptance still needs a known drop sequence and
visible cooking/alchemy completion/absence screens; tests are not substitutes.
