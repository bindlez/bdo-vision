# rc.28 — Craft companion test

1. Close the old Vision app, extract the new Windows ZIP into a fresh folder and
   run **OPEN-BDO-VISION.bat**. Existing history stays in the shared profile.
2. In Craft, choose **Craft overlay**, or Grind → Open game overlay → **CRAFT**.
3. Click **WEBSITE** in the sidecar once. Keep this dedicated companion tab open:
   it runs the same calculator as the website and receives requests over an event
   connection. The native sidecar contains no second recipe calculation engine.
4. Search cooking/alchemy recipes. Enter maximum LT, carried LT before extra
   packing, reserve LT and remaining tool uses. A read tool supplies its current
   countdown estimate; explicitly edited budgets remain manual inputs.
5. **FILL MAX** calculates the load. Edit any ingredient and press Enter to link
   the others to whole-craft ratios. Check **Edit independently** to enter each
   amount; the limiting ingredient determines crafts and leftovers.
6. Inspect max crafts, time, expected output, gross/net silver and net/hour.
   Missing prices remain unpriced; the existing shared price cache refreshes on
   demand. Modeled output and input costs are estimates, not a sale receipt.
7. Click **TIMER** for a load that fits. The website starts one planning timer;
   begin crafting yourself in game. Expired requests and duplicate retries cannot
   silently restart a timer. Cooking and alchemy's existing planner run rules remain.

## Inventory snapshots

Craft → **Read inventory** gives you 1.8 seconds to return to BDO with Inventory
visible. **Toggle I-key snapshots** enables optional observation of I-key presses;
the key is not intercepted or injected. A hidden/closed inventory yields no
snapshot. An active read is skipped if another reader is busy. Lite Use prevents
capture. Readers → **Inventory reader** shows actual input and both engine results.

Current snapshots contain **carried/max weight only**. Item icon identities and
stack counts are unknown. This is not a complete bag scanner. **USE SNAPSHOT**
applies the last reading, including its timestamp. Inventory changes after that
reading require another snapshot. Existing ingredient stacks are not subtracted
from packing weight until their counts are known in the full website model.

## Other additions

- Drag the main HUD to move its docked crafting panel. Drop reveals avoid both.
- **Show labeled forecasts during capture gaps** controls retained craft forecasts.
  Forecasts never enter the ledger; a new tool needs its own verified craft context.
- **Celebrate captured craft milestones** is optional. Only accepted recorded
  units count; popup mute, reduced motion and optional sound remain in Overlay settings.
- Grind runs receive date/time labels. Exact trash signatures currently cover
  Tungrad Ruins and Yzrahid Highlands. Shared rare drops never prove a spot, and
  conflicting trash produces an ambiguous state. Choose a spot override if needed.
- Planning → **Fairy desktop** opens a read-only compact treasure catalog and
  recorded family finds. The full website retains collection ownership/simulators.
- CP desktop's chart selector includes EXP and opportunity-cost pies.

## Acceptance still needed in game

Verify I-key capture on your current UI scale, compare LT with the actual game,
check ratio edits and an actual cooking/alchemy timer, and test docking on your
monitor arrangement. Record any mismatch with the Inventory reader or existing
Tool/Quest/Loot debug pages. No universal OCR or zero-FPS-impact claim is made.
