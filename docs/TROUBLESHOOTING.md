# Troubleshooting

## Send Now does not update the planner
1. Close older BDO Vision instances (check Task Manager).
2. In the **same** desktop app, click **Open Planner**, not a saved HTML bookmark.
3. Click **Send Now**, then **Test Link**.
4. `Bridge READY` means the server is listening; `PLANNER SYNC CONFIRMED` means the website accepted the message. These are different states.
5. If `7283` is occupied, the app tries ports through `7292`. Always open the planner from the current app.

## OCR reads 1350 instead of (350
The parser applies the correction only if the active timer strongly supports ~350. When starting without an established reading, confirm the correct number manually rather than automatically stripping a legitimate leading 1. Keep the full `current/max` label in the selection box.

## Auto-scan does not trigger
The game must be visible and foreground. In tray mode there are no pixels to capture. Set the OCR area to include the durability digits, and check that Tesseract exists at the path in Settings.

## Super Restore does not work
Windows notification area icon labels and BDO versions can vary. Install tray support with `INSTALL-TRAY-SUPPORT.bat`. If BDO is in native tray mode and automation cannot find the correct icon, click the BDO tray icon manually.

## Alarm timing drifts
Specify the actual seconds per craft; a fixed duration is an estimate, not a detected craft tick. Another OCR measurement re-anchors the estimate.
