# BDO Vision: useful first, fast always

## Working brief

Improve the existing product in place. Make the website the primary crafting
workspace and the Windows app a compact capture/timer/alert companion with direct
website shortcuts. Preserve every existing page, history record, export, timer,
reader debug view, tray control and optional sharing preference. Do not build a
second independent calculation system in the launcher.

The core journey is: scan the current tool → identify the output being crafted →
see recorded loot, expected costs/value, remaining time and the stopping rule →
inspect the production line, ingredients or CP decision in one click → get an
actionable alert. Tool durability remains the default for cooking and alchemy;
ingredient and hybrid rules remain independently selectable for either skill.

Use the approved dark/violet/teal overlay style. Make interaction obvious and
keyboard accessible. Reward genuine accepted drops; do not invent earnings,
probabilities, missing items, quest absence or completion. Keep models separate
from observations. Preserve Lite Use and held tool OCR. No gameplay automation.

## Ordered implementation and acceptance checklist

- [x] **Access audit:** list every native page; expose direct destination buttons
  instead of nested Planning/History/Readers menus. Verify all notebook pages have
  a route and preserve selection after reopening. Keep full legacy tools available.
- [x] **Website crafting desk:** show overview, quantities and ingredients without
  disclosure nesting. Add permanent quick access for weight/packing, map/timeline,
  production steps, outputs, cost/tax, graphs, character settings and queue. Keep
  the searchable recipe book visible by default. Preserve models and stored plans.
- [x] **Core live status:** surface tool remaining/time, craft detection, loot
  availability and last-seen guild information together using the existing bridge.
  A fresh bridge response is not a fresh OCR observation. Explain the next action
  when capture, prices, a tool, or a detected recipe is missing. Link CP Info.
- [x] **Overlay foundation:** compact passive HUD, Big/Huge/Treasure reveals,
  bounded queue, no duplicate moments, partial/unpriced states, optional sound,
  reduced motion, dismissal and snooze. Preview never writes loot/history.
- [x] **Intuitive snapping:** saved monitor-aware positions, edge/corner snapping,
  a visible drag target and live snap feedback. Tile reveals beside the HUD;
  clamp after monitor changes, respect taskbars and negative desktop coordinates.
  Lock/click-through must remain recoverable from the launcher.
- [x] **Guild alert repair:** verify the reminder runs when crafting starts and
  after a paired quest read, including a completed mission screen. Fresh explicit
  absence/completion gets an actionable notification. Unknown/covered/stale cards
  remain unverified. Deduplicate, respect sound/snooze, expose state on the website.
- [x] **Loot reliability:** inspect configuration, feed consensus, row alignment,
  capture gaps and reader contention before changing speed. Add regressions for
  any proven failure. Expose last capture/read/save and uncertain-row reasons.
  Never count an OCR guess to make a total look complete. Live acceptance needs
  a known sequence of actual drops; report that limitation explicitly.
**Release gate:** run native and shipped-browser regressions, docs/links, Windows
  packaging self-check and checksum validation. Provide a runnable sample preview
  and versioned ZIP. Do not replace a running app or edit the real profile to test.

## Relationship between features

The accepted loot ledger is the source for silver, craft inference, sessions and
Big Drops. Tool state supplies the timer and the craft forecast. Quest snapshots
travel alongside tool acquisition, with the existing opt-in small-card watch.
The bridge supplies one read-only live context to the website; recipe/market/CP
models stay website-owned. Navigation and overlays are presentations of those
same sources, not new readers or independent histories.

## Evidence rules and performance limits

No new runtime dependency, capture loop, idle animation, global hook or game
injection. Reuse existing one-second UI updates. Overlay animation runs only for
a bounded reveal; layout checks run on movement/settings. Keep queue/storage
bounded. Check functionality first, then report measured tests separately from
live-game accuracy. Never claim 100% OCR or a measured FPS improvement without
the relevant held-out/live evidence. Public artifacts contain synthetic examples,
never user profiles, screenshots or diagnostic logs.

This checklist is updated with concrete evidence in the release handoff; unchecked
reader acceptance items must not silently become production-verified claims.


## rc.27 evidence and remaining acceptance

Implemented items above passed 428 native regressions plus shipped planner,
security, calculation, navigation and documentation checks. The incomplete-feed
recovery matched all eight rows/counts in one privately held failed capture,
versus five before. It reused the existing helper; no screenshots or profiles are
included in this source. Artifact checksum and extracted Windows self-check are
recorded alongside the versioned ZIP in the release center.

- [ ] Verify a known-count live grind sequence, including one rare drop.
- [ ] Verify the completed/no-active mission prompt during live cooking/alchemy.
- [ ] Verify snapping across the user's actual display scales and fullscreen mode.

These are explicit live-acceptance gates, not features removed from the product.
No universal OCR accuracy or game-FPS claim is made from the automated suite.
