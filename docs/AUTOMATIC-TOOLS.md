# Automatic cooking/alchemy tool reader

Automatic tool discovery is enabled by default. Show the game in front with utensil labels visible; no capture box is required. Use **NEARBY TOOLS** to see verified durability, percentage remaining and active-use evidence. Manual region OCR remains an optional fallback in Settings.

The reader finds a likely character anchor from paired in-world red/blue bars, with screen center as a search prior when those bars are absent. It reads a narrow band above that anchor at higher resolution, then automatically isolates numeric fractions for two focused OCR reads. It searches outward when needed and can use an OCR-detected **Place Mode** button as a fallback reference. No rearrangement of the game's UI is required.

The character anchor found more candidate labels than the Place Mode band in the three private test frames, with similar narrow-scan time (~0.6–0.7 seconds versus ~1.6–2.2 seconds for whole-frame sparse OCR). These are small discovery measurements, not an FPS comparison or complete accuracy benchmark. The final focused-number path recovered 95/3000 and then 82/3000 on moved-camera captures while another tool remained 2472/3000. Names obscured by overlapping labels are explicitly marked as partly covered.

## Active-tool evidence

Position prioritizes the search; it never proves which tool is active. Selection needs a unique tool with two separate plausible durability decreases. Camera movement triggers reacquisition. Name/type, capacity and durability history distinguish tools after they change screen position. Identical, conflicting or unreadable tools remain unconfirmed. Replacement tools require fresh use evidence. Brief confirmation reads are three seconds apart; confirmed monitoring follows the configured interval, capped at two minutes. When no labels are visible, discovery backs off rather than continuously OCRing the screen.

Only currently visible labels can be measured. Zooming a label off-screen or hiding it behind a window removes the measurement; the reader reacquires it when visible again. Moving the camera does not require recalibration. A previously automatic estimate pauses if its active tool can no longer be confirmed. Tool data cannot reveal furniture behind walls or names/durability that are not rendered by the game.

At most eight candidate labels are processed per pass, with a six-second OCR work budget and below-normal, single-thread workers. Cached crops are used between broad discoveries; failed crop locations trigger a new search in the same scan. No game input is generated. Screenshots remain transient in memory. The existing loot reader, saved history, optional sharing and manual planner-send controls are retained.

Automated tests cover multi-tool ambiguity, unrelated HUD fractions, damaged digits, missing labels, replacements, camera shifts, no initial region selection, and actual Tesseract reads of generated scenes. Real-world overlap/font/zoom coverage remains under validation; keep 1.11.1 as a known working fallback.
