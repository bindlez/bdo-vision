# 02 · Architecture and ownership

## Runtime flow

`desktop/app.py` owns the Tk root, shared reader coordination, the craft countdown, settings and bridge lifetime. `LootTrackerUI` owns loot capture and ledger updates. `GuildQuestTracker` owns quest scheduling and persistent quest state. Recognition modules return observations; UI controllers decide how those observations affect the product.

The normal path is: verify the visible BDO window, capture a bounded region, recognize in a background worker, validate a result, deliver it to Tk with `root.after`, commit accepted facts, update a bounded bridge snapshot and refresh the visible UI. Capturing a frame is not proof it was readable. Reading a counter is not proof the tool is in use. Sending an HTTP update is not proof a browser applied it.

## Ownership boundaries

| Layer | Owns | Must not do |
| --- | --- | --- |
| Recognition | Image preprocessing, literal extraction, consensus and bounded caches | Write the loot ledger, select browser timers or send game input |
| Controllers | Reader scheduling, cancellation generation, UI state, accepted observations | Block Tk with OCR or silently manufacture missing observations |
| Pure domain code | Counter gates, feed overlap, clocks, valuation, planning formulas | Read Tk variables or depend on a foreground game window |
| Persistence | SQLite history, settings, profile backups, gear backups | Treat an extracted ZIP as the only copy of user history |
| Bridge | Local HTTP validation, frozen snapshots and bounded commands | Access Tk widgets from HTTP worker threads |
| Browser | Planner interactions, render state, cached prices, user decisions | Claim it has native BDO access in an offline demo |

The source atlas indexes the actual functions and classes for every source file. It includes test helpers and experimental native code, with those distinctions retained. The contracts page extracts SQLite declarations and literal settings keys from the current code, so names are directly traceable to their implementation.

## Important clocks

Use `time.monotonic()` for elapsed work budgets, scheduling and consumption intervals. Use wall time for user-facing capture timestamps, saved observations and cross-process messages. Timer anchoring uses capture time, not when OCR finishes; otherwise slow recognition creates phantom remaining durability.

`capture_clock.py` tracks observed and excluded periods. `tracking_core.py` guards accepted durability. `scan_engine.py` controls pass selection, stability, publication and passive pace estimation. A craft countdown is an estimate of continued crafting. Loot and quest counts are observed facts. Keep those categories distinct in both data and labels.

## Background work

Readers coordinate through busy flags and scheduled callbacks. Quests have a waiting flag to avoid starvation behind repeated loot/tool work. Workers are daemon threads, and the UI receives their results through callbacks. A generation counter makes old work harmless after a region or tracking mode changes. Bridge snapshots are copied under locks. SQLite connections are owned by the side that created them; bridge queries use their own appropriate connection path.

## Current technical debt

The native controller and single-file planner still contain large sections of code. Extracting them is useful only with stable behavior tests. Do not reformat every module or translate the runtime in one change: it obscures the exact OCR change being tested. [The improvement plan](16-maintenance.md) prioritizes incremental seams and records which work remains.
