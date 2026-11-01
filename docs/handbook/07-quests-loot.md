# 07 · Quests and loot are separate observation systems

## Quest scoping

The Guild parser requires a heading containing Guild, Alchemy and a mission/quest/supply indicator. It finds the matching obtain/produce/make/craft/perform objective and collects a bounded continuation block. A new objective or quest heading ends that block. This is why the Daily oil counter cannot be substituted for the Guild Catalyst counter.

The visual widget can place `49/` on one line and `600` on the next, or move `101/600` to the next line. The parser joins a bounded objective block rather than assuming a fixed counter row. Harmless separator punctuation is normalized, but damaged digits and ambiguous pairs are rejected. Both broad OCR passes must agree. If they fail, bounded gold-heading discovery and a focused body pass can recover the scoped objective within the existing three-second budget.

Daily and Bonus objectives are independently keyed by kind and normalized objective text. Only their agreed counters update their rows. The in-memory/persisted collection is bounded. OCR spelling changes can still create distinct keys; robust alias reconciliation is future work and must not merge different real objectives by guesswork.

## Quest lifecycle

`GuildQuestProgress` stores the last verified counter and observation timestamp. It alerts once near the configured threshold and once at completion. The default near threshold is 95%. A lower counter can mean a new mission, but can also be a bad read. A refilled visible mission timer and repeated consistent observations support rollover. Older saved state has a guarded migration path. Pausing never extrapolates quest credit.

When a craft is sent to the planner, the last seen Guild snapshot can be included. The website displays its observed count and timestamp, not a fabricated forecast. Tracking itself is optional. The Quest OCR reader is also optional and has no separate scanning loop.

## Loot extraction lifecycle

`recognize_feed` prepares bounded masks, performs OCR and parses item events. `item_events.py` handles names, quantities, message fragments and agreement. `LootSnapshots` handles notification changes; `TextFeedSnapshots` handles scrolling feed overlap. The controller writes only newly accepted events to `LootLedger` and updates optional sharing.

Do not replace overlap logic with a set of item names. Two identical lines can represent two real drops. Conversely, the same visible message across multiple frames is not repeated loot. Lost scroll overlap, unreadable quantities and uncertain names must be visible diagnostics rather than silent credit.

The loot capture budget rejects accidental huge regions. The target interval is not the actual end-to-end gap: capture, recognition and shared-worker contention add latency. A feed that scrolls away between scans cannot be perfectly reconstructed from the remaining pixels. Explain the displayed scan time/gap rather than promising polling alone guarantees recall.

## Testing a change

Test wrapped quest layouts, independent personal counters, mission rollover, thresholds and stale state. For loot test repeated identical drops, mixed messages, quantity suffixes, split names, bundle names containing xN, scrolling overlap and unknown catalog names. Validate the path through ledger insertion; a correctly parsed string alone does not prove a correctly recorded event.
