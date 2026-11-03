# 23 · Structured tool and guild readers

The old general OCR locator remains available as a fallback. The new route uses
Windows' English OCR service for positioned text, followed by independent literal
Tesseract verification of the relevant numeric field or guild card. It is a
different recognizer/localization route, not another inversion of the same OCR
output. No new Python package is required. Tesseract remains required for numeric
verification and the other existing readers; do not call the application fully
dependency-free.

## Ownership and execution

- `native/windows_ocr_worker.cpp`: bounded binary PNG-in/JSON-out pipe worker using
  Windows Runtime APIs; English language support must already be present. Runs
  below normal priority. No screenshot files, network access or gameplay input.
- `desktop/windows_ocr.py`: lazy process creation, serialized requests, deadlines,
  bounded responses and shutdown. An unavailable engine is a recoverable state.
- `desktop/structured_reader.py`: positioned title/counter fields, Place Mode
  association, independent guild-card verification and conservative fallback.
- `desktop/tool_reader.py`: literal numeric voting, identity/use tracking and
  countdown acquisition. A Windows-read pair must exactly match its independent
  numeric verification before it is accepted.
- `desktop/guild_reminder.py`: pure event-driven reminder rules and deduplication.

Build with `native/build-windows-ocr.cmd`. Windows release packaging includes the
helper under desktop assets. Windows SDK/MSVC are development requirements, not
end-user installers. `structured_reader: false` in settings retains the compatibility
route. An absent helper or unavailable Windows English OCR also falls back explicitly.
The bridge/debug views must not describe fallback results as Windows-verified.

Tool acquisition prioritizes one positioned candidate near Place Mode. Position
only chooses a crop; it does not validate a number. Damaged text can identify where
to read, but cannot replace missing digits. Full literal agreement and existing
plausibility checks remain. The countdown/latching/Lite Use contracts are unchanged.

Guild cards keep both possible counter rows. Two engines must agree on the exact
counter and the same objective. A long known item-name typo can use the existing
unambiguous catalog resolver; numbers are never repaired. Cooking and alchemy
headings are supported. Daily/Bonus cards remain separately scoped.

## Missing quest reminders

An optional setting, enabled by default, reminds after existing tool/quest
acquisitions. It adds no scan scheduler. Fresh matching progress suppresses the
reminder. Completed quests suggest claiming and accepting a new mission. Literal
no-mission text needs two recognition votes before it is treated as absence.
An absent/covered/disabled/stale reading only produces a quiet **not verified**
message. It must never prove that the guild has no active quest.

Reminders deduplicate by tool session and state; a ten-minute snooze is available
on the Quests page. Lite Use does not resume OCR for reminders. Missing/uncertain
quest state never stops the crafting countdown or creates quest progress.

## Evidence and limits

Two saved reference frames read 2492/3000 and 2491/3000 using the new route in about
0.32–0.36 seconds, with three recognition operations per acquisition. A fresh private
live reference with overlapping labels required the compatibility tool route and
read 2950/3000. Its wrapped guild 0/600 read through independent engines in about
0.44 seconds after catalog-based objective-name normalization. These are individual
frame observations, not a general accuracy percentage or a changing live timer test.
No universal 100% accuracy, FPS or orders-of-magnitude performance claim is supported.

The test runner disables external OS workers in general controller fixtures.
Structured-reader tests inject their own worker/positioned output. Real private
captures stay outside versioned source. Required live acceptance still includes
camera movement, overlapping labels, both wrap heights, tool swaps, completed/absent
quests, low durability, background/occlusion and a full Lite Use run.

[Microsoft OcrEngine API](https://learn.microsoft.com/en-us/uwp/api/windows.media.ocr.ocrengine)
describes the recognizer and platform/language requirements. The local probe is
the capability check; unavailable systems keep the compatibility reader.

See the [complete prioritized checklist](../ACTIVE-TASKS.md).
