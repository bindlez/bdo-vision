# 07 · Quests and loot are separate observation systems

## Quest scoping

The Guild parser requires a heading containing Guild, Alchemy and a mission/quest/supply indicator. It finds the matching obtain/produce/make/craft/perform objective and collects a bounded continuation block. A new objective or quest heading ends that block. This is why the Daily oil counter cannot be substituted for the Guild Catalyst counter.

The visual widget can place `49/` on one line and `600` on the next, or move `101/600` to the next line. The parser joins a bounded objective block rather than assuming a fixed counter row. Harmless separator punctuation is normalized, but damaged digits and ambiguous pairs are rejected. The reader first tries bounded gold-heading cards, keeping the entire widget width below each header. The objective and wrapped counter can begin left of the indented gold title; cropping at the title x-coordinate clipped leading digits. Two focused body passes must agree on counter and objective, with the next gold heading ending the card. Broad/completion fallback shares the same three-second budget.

Daily and Bonus objectives are independently keyed by kind and normalized objective text. Only their agreed counters update their rows. The in-memory/persisted collection is bounded. OCR spelling changes can still create distinct keys; robust alias reconciliation is future work and must not merge different real objectives by guesswork.

## Quest lifecycle

By default, quest reads are paired with tool attempts. `App.capture_tools` can crop the quest area from its full screenshot; `finish_tool_attempt` applies the tool result before requesting `GuildQuestTracker.scan(paired=True, sample=...)`. Enabled tracking, the original reader instance and quest generation must still match. Missing shared images use a bounded quest capture; stale/mismatched generations do not pair. The scheduler is disabled unless the user explicitly opts into Smart quest watch. SCAN TOOL + QUEST requests a tool scan. If loot or another reader is busy, a paired read queues in 100 ms steps for at most three seconds rather than being silently discarded; generations cancel stale work. Off, queued, reading, partial and saved snapshots have distinct actions and diagnostics. Counts and completion remain last seen between tool attempts, including Lite Use and while confirmed crafting holds tool OCR. Alerts reflect observed verified snapshots only. Optional Smart quest watch checks at 15-second intervals only while the craft timer runs, enabled tracking is on, and Lite Use is off. It uses the last verified small guild-card geometry, reuses exact verified pixel hashes for up to 60 seconds, and reacquires the full widget after the card stops verifying or window geometry changes. Covered areas do not yield new progress. No watch callback exists while this option is off. Lite Use cancels it; tool OCR remains held. The option defaults off for existing profiles.

The completed guild widget can replace the numeric objective with `The guild mission is complete.` or the wrapped instruction `Claim your rewards via the "Complete Mission" button in the Guild Mission window.` Two existing broad passes must independently recognize one of these literal messages. The reward instruction is guild-specific and works when the heading is occluded. Ordinary personal `Complete`, negation, conditional instructions and incomplete-counter conflicts do not qualify. No new capture loop or completion OCR pass is added.

Visual completion has independent `completion_at`, `completion_seen_at`, `completion_basis` and bounded evidence fields. It sets the displayed status to **Guild quest: Complete**, without changing the last numeric `current`, `target` or `last_at`. It can be saved before any numeric counter exists. Completion alerts deduplicate across restart; identical verified reads refresh in-memory freshness without a database write each time. A new incomplete quest requires two separate consistent reads before clearing visual completion, including when its count is the same as the old last numeric value. NEXT QUEST clears the completion. A blocked or stale widget retains a visibly last-seen completion, never fresh inferred progress.

The bridge's frozen craft receipt includes `complete`, `completion_at` and `completion_basis` but excludes raw evidence and images. The planner accepts a valid completion with nullable numeric fields, renders **Guild quest: Complete**, and labels any retained numeric counter as last seen. It does not manufacture a target-equal count or continuously rewrite a finished receipt.

`GuildQuestProgress` stores the last verified counter and observation timestamp. It alerts once near the configured threshold and once at completion. The default near threshold is 95%. A lower counter can mean a new mission, but can also be a bad read. A refilled visible mission timer and repeated consistent observations support rollover. Older saved state has a guarded migration path. Pausing never extrapolates quest credit.

When a craft is sent to the planner, the last seen Guild snapshot can be included. The website displays its observed count and timestamp, not a fabricated forecast. Tracking itself is optional. The Quest OCR reader is also optional and has no separate scanning loop.

## Loot extraction lifecycle

`recognize_feed` prepares bounded masks, performs OCR and parses item events. `item_events.py` handles names, quantities, message fragments and agreement. `LootSnapshots` handles notification changes; `TextFeedSnapshots` handles scrolling feed overlap. The controller writes only newly accepted events to `LootLedger` and updates optional sharing.

Do not replace overlap logic with a set of item names. Two identical lines can represent two real drops. Conversely, the same visible message across multiple frames is not repeated loot. Lost scroll overlap, unreadable quantities and uncertain names must be visible diagnostics rather than silent credit.

The loot capture budget rejects accidental huge regions. The target interval is not the actual end-to-end gap: capture, recognition and shared-worker contention add latency. A feed that scrolls away between scans cannot be perfectly reconstructed from the remaining pixels. Explain the displayed scan time/gap rather than promising polling alone guarantees recall.

## Testing a change

Test wrapped quest layouts, independent personal counters, mission rollover, thresholds and stale state. For loot test repeated identical drops, mixed messages, quantity suffixes, split names, bundle names containing xN, scrolling overlap and unknown catalog names. Validate the path through ledger insertion; a correctly parsed string alone does not prove a correctly recorded event.
