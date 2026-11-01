# 04 · State, storage and safe migrations

## The profile is the user's product

The default profile is `%USERPROFILE%/.bdo-vision`, resolved by [storage.data_root](../../desktop/storage.py). `BDO_VISION_DATA_DIR` overrides it for isolated tests and development. Application files and user data have separate lifecycles. Removing or replacing an extracted release must not remove history.

| Data | Location or owner | Notes |
| --- | --- | --- |
| Loot and related tables | `loot-history.sqlite3` in profile | Authoritative accepted event history; never replace it to switch app versions |
| Native preferences | `settings.json` | Preserve unrelated keys when modifying one setting |
| Runtime identity | `runtime-status.json`, `instance.lock` | Transient instance coordination, not a durable session receipt |
| Profile backups | `backups/` | SQLite-consistent backups with integrity verification |
| Market item index/cache | Profile files and quote tables | Rebuildable knowledge, not a replacement for the event ledger |
| Equipment backups | `gear-builds.json`, `gear-builds.previous.json` | Validated JSON backups; browser state also exists |
| Planner and gear state | Browser localStorage | Scoped to the browser origin; another port, browser or file URL may show different state |

## Ledger contract

`LootLedger` stores an ID, timestamp, session, item, quantity, source and kind. Quantity must be an integer in the supported positive range. `kind` was added through an additive migration with default `Drop`; older rows remain intact. Its in-memory revision changes when rows are added or reclassified. Consumers can use that revision to avoid rebuilding unchanged summaries.

SQL statements use parameters for values. Do not concatenate item names into SQL. CSV export protects formula-like strings so opening an export in a spreadsheet does not interpret an item name as a formula. The generated contracts page shows the actual table declarations, including quests and quotes; consult the implementation for migrations and indexes.

## A safe schema change

First write a test that constructs the old schema with representative rows. Apply your migration using a temporary profile, verify every old row and count, then open the profile again to prove the migration is idempotent. Prefer additive columns and new tables. Keep interpretation of older rows explicit. Record whether older versions can open the new schema before offering a downgrade.

Back up a live database through SQLite's backup API. Copying an actively changing database file with an ordinary filesystem copy is not a reliable substitute. `copy_database` runs an integrity check on the saved database. A release upgrade should acquire `InstanceLock`, back up, install, verify the resulting profile and release the lock before reopening.

## Recovery rules

Restore code independently of data. Never merge two overlapping captured histories by blindly concatenating rows: the same loot may exist in both. To investigate a suspected loss, preserve all candidate databases, compare their time ranges and identities, and work on copies. A Git tag protects source; it does not back up the user's history or browser localStorage.

## Debug data

The new Tool and Quest OCR viewers retain their previews only while open. They do not write screenshots, create a separate poller or expose image paths through the bridge. Other diagnostic tools may write captures when explicitly used; treat those outputs as private and keep them out of source control and release artifacts.
