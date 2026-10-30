# 1.8.1 release review

## Findings from the live grind test

- Transient popup captures often contained scenery after a notification disappeared.
- Plain grayscale blended outlined text into moving terrain. This rejected several item types; it was not a Shining Powder-specific issue.
- Loot capture waited for unrelated durability OCR, reducing the effective sampling rate.
- Multiset message voting could reorder repeated drops and rare items before chat deduplication.
- A damaged quantity such as `xT` could fall back to an implicit one during name matching.
- The previous workflow attempted Windows-native tests on Linux without installing dependencies.

## Changes

- Outlined-text filtering learns repeated item-quality colors from each frame. Broad color filters were tested and replaced because they retained terrain.
- Ordered row voting preserves repeated drops and item order. Two complete agreeing reads can exit early.
- 0.5-second target scans are available. Displayed OCR time and capture gap show actual throughput; the target is not a guaranteed frame rate.
- Loot scans no longer wait for durability OCR to finish.
- Unreadable chat slots stay in place. Newly arrived unreadable slots can recover on subsequent captures; retained rows are not counted again merely because OCR improves.
- Lost scrolling overlap is shown; uncertain drops are excluded.
- Broken quantity fields are rejected instead of assumed to be one.
- Version identity, Windows checks, clean packaging and SHA-256 manifests were added.

## Evidence

113 isolated Windows regressions passed locally, including native widgets, screenshot OCR, bridge controls, history, sessions, prices and tray behavior. Planner JavaScript syntax passed. Private grind captures were replayed locally: an eight-row sequence with seven Tungrad drops and Laila's Petal was read in order with the displayed quantities in about 0.75 seconds. Live 1.8.1 also read complete eight-row frames and appended new Tungrad batches to the existing ledger. This is a targeted test, not a measured total-session accuracy claim.

Captures, databases, market cache, settings and user history remain outside Git. Public source generates branding and synthetic fixtures. GitHub CI results must be checked separately.

## Next improvements, in order

1. Measure capture recall against an independently counted short run; show visibility gaps and lost-overlap counts in a session-quality summary.
2. Benchmark a persistent OCR worker with bounded buffering, capture-time session assignment and a drain step before finishing a run.
3. Investigate visual scrolling evidence for identical rows. Pixel-identical repeated rows cannot prove another drop occurred; do not infer loot from time alone.
4. Add explicit Pause and Resume actions checked against the intended session, replacing the toggle for remote controls.
5. Explain capture setup by feed and surface missing rare-panel setup in popup mode.
6. Add a signed Windows installer/executable pipeline after source-build CI is verified.

## Limits

The persistent personal obtained-item feed is recommended for grinding because it retains multiple drops longer than popups. Keep 6–8 complete rows visible, with names and quantities inside the selected region. Use one feed at a time to avoid counting the same drop twice. Fast scrolling, blocked text, unreadable rows and identical retained rows can still undercount. No unseen loot or missed historical quantities are reconstructed. Silver is item value before costs/fees, not sale proceeds. A restarted session requires Resume; global recording can continue while its session timer is paused.
