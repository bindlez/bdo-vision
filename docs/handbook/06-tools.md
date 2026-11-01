# 06 · Current tool and durability

## Discovery and first selection

`AutomaticToolReader` prefers a small high-resolution header search for Place Mode. It uses that button as an anchor for nearby tool labels, with character-bar and broader scene fallbacks. Gold durability bars and OCR geometry locate candidate names and numeric fields. The reader caps the number of tools and rejects conflicting duplicate locators.

`verify_labels` reads the numeric crop in two polarities. Both readings must contain the same valid current/maximum pair. Initial bar evidence can reject a numeric reading that conflicts with the approximate fill. Exact verified crop hashes can be reused briefly; the numeric cache is bounded. Title signatures ignore changing digits but detect moved labels, triggering rediscovery rather than reading stale coordinates.

`place_selected` ranks verified nonempty fields near and below Place Mode. It uses the numeric field center when available, scales its tolerance by client height and refuses near ties. The first such selection can start the countdown immediately and is labeled as selected by position. It does not claim the tool has already demonstrated consumption.

## Confirming use

Ordinary inventory tracking requires repeated plausible decreases for one tool. Matching considers family, capacity, durability history and elapsed time; it can preserve identity when the camera moves. A single missing frame does not publish a hidden active tool. Repeated gaps clear use evidence. An increase is treated conservatively as a replacement/refill rather than normal consumption.

The timed fallback captures two batches of existing label crops about 1.5 seconds apart before OCR. It verifies stable labels, matching fields and capacities, two numeric votes per observation and one unique plausible decrease. The acceptable interval is bounded; delayed batches cannot qualify. It rejects increases, unreadable neighboring fields, multiple changing tools and movement. A timed change that disagrees with a unique Place Mode selection does not confirm the neighbor.

The timed fallback is rate-limited and shares the six-second tool work budget. A confirmed reader does not add another timed pair. A provisional Place Mode selection schedules a quicker follow-up. This may be expensive if the tool stays visible but idle; an evidence-preserving backoff is a future optimization to benchmark, not an undocumented behavior guarantee.

## Countdown versus verified value

The tool table has verified durability and an estimated durability column. Estimate equals the verified value minus whole uses since the observation, using a measured or configured craft interval. It assumes continued crafting and is labeled accordingly. It does not require another image read. The application gate handles new sessions, maximum changes and suspicious jumps before synchronizing the craft timer.

## Edge-case checklist

| Situation | Required behavior |
| --- | --- |
| Several tools below Place Mode with similar scores | Keep selection uncertain |
| Empty tool nearest button | Do not start it from position alone |
| Wrong nearby tool decreases | Withhold confirmation when it conflicts with Place Mode |
| Both tools decrease | No unique use confirmation |
| Refill or replacement | New identity/evidence, not negative consumption |
| Camera pans during paired capture | Reacquire, do not compare mismatched fields |
| Capacity or name family changes | Do not carry use evidence across incompatible identities |
| Partially covered name | Preserve explicit partial identity; do not invent a prefix |
| Window hidden or blocked | Pause verified tracking; show previous value as stale |
| OCR loses a leading digit | Reject damaged text; never repair digits from expectation alone |

Use `python dev.py test tool_reader tool_status tracking_core auto_ocr` after changing these rules. Test multiple tools with equal counts, movement, zero, refills and jitter, not just the happy path.
