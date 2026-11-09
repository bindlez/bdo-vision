# 05 · OCR architecture and accuracy rules

## There are several readers

| Reader | Production path | Distinct responsibility |
| --- | --- | --- |
| Loot | `loot_capture.py` → `item_events.py` → snapshot/ledger | Personal obtained-item messages and item-drop feeds |
| Automatic tools | `tool_reader.py` → `ToolInventory` → controller gate | Locate tools, verify durability, identify current tool |
| Manual durability region | `app.py`, `ocr_parser.py`, `spatial_ocr.py` | Existing region-based craft reading and conservative timer acceptance |
| Quests | `guild_quest.py` → `GuildQuestProgress` | Scope Guild/Daily/Bonus counters and track observed progress |
| Equipment | `gear_sweep.py`, `gear_ocr.py` | On-demand tooltip and image import, followed by review |

All use local image/text recognition. `ocr_runtime.run_ocr` limits OpenMP threads to one and gives subprocesses below-normal scheduling priority on Windows. That reduces interference but does not prove zero FPS impact. Every pass must have a timeout and a finite work budget. Do not add an always-running web worker or native reader merely because one is available.

## Accuracy means both precision and recall

Precision asks whether accepted events are correct. Recall asks how much real loot or progress was missed. Requiring agreement improves precision but may reduce recall. Never improve a headline recall number by accepting damaged quantities, borrowing a nearby quest counter or inventing hidden loot. Record false positives, false negatives, unresolved items and latency separately.

Two transformations of the same image are not statistically independent observations. Their agreement is a practical consistency check, not a proof of truth. Timed frames add evidence of change but can still be affected by camera motion, occlusion and correlated recognition errors.

## Coordinates and capture time

Windows capture bounds are `(window_id,left,top,right,bottom)`. User-selected regions are generally `(x,y,width,height)`. Tool regions are relative to the verified client image; adapters add the client origin exactly once. A crop stored in image coordinates must not be reinterpreted as desktop coordinates. Test nonzero monitor origins and moved windows.

Use the screenshot's timestamp to anchor accepted values. Worker completion time includes OCR latency and cannot be substituted. When BDO loses focus during a tool crop batch, discard the batch. Quest reading may use a visible uncovered background game area, but must verify the exact region is not occluded.

## Debugging a miss

Open the reader for that feature, request a scan and return to BDO so the app is not covering the source. First inspect the image: does it include the complete intended text? Then inspect recognized text, scoped fields and the rejection reason. If the image is wrong, fix discovery or geometry before changing digit recognition. If text is readable but rejected, add the exact text as a synthetic parser regression. If OCR itself is wrong, keep a private annotated frame and compare bounded preprocessing alternatives.

The Tool viewer displays the discovery scene or current label crops, verified fields, anchor, status and bounded raw OCR output. The Quest viewer displays the actual resized input, two-pass text and accepted result. Exact-pixel cache hits may have no new raw tool text; they still show the image and verified result. Closing a viewer releases its preview; reopening cannot display an old worker's result.

## Acceptance and evidence levels

A recognized string is a candidate. Two matching valid numeric reads produce a verified durability field. Place Mode proximity produces an initial tool selection. Repeated plausible decreases or a valid timed comparison produce use confirmation. The UI must preserve those distinctions. Quest values are last seen, not estimated. Gear imports require review. Missing and stale values stay explicit.

No complete real-world accuracy claim is made by the regression suite. Saved bright-background guild text remains a known difficult case. [Testing](11-testing.md) explains the distinction between generated fixtures, private replay evidence and a live game check.

## Future capture option

Test Windows Graphics Capture against a verified BDO window in borderless
mode. Compare fresh frames with the game visible, covered, minimized and in
native tray mode. Validate client-area coordinates and DPI before cropping.
Reject missing, stale or black frames. Keep the current screen capture path
for unsupported configurations. This is a possible window-frame source.
Production does not use it yet.

[Microsoft window capture API](https://learn.microsoft.com/en-us/windows/win32/api/windows.graphics.capture.interop/nf-windows-graphics-capture-interop-igraphicscaptureiteminterop-createforwindow)
