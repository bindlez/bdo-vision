# Architecture and event lifecycle

1. **Desktop** `desktop/app.py` captures the configured screen region when BDO is foreground.
2. **OCR** Tesseract runs in a background thread. `ocr_parser.py` scores candidate reads conservatively.
3. **Timer** is anchored to the screenshot observation time, so OCR latency does not add phantom durability.
4. **Bridge** `planner_bridge.py` serves the matched planner on localhost and exposes the legacy `GET /durability` payload.
5. **Browser** polls updates, matches the `instance_id` and `session_id`, starts or updates the tool session, then acknowledges via `POST /ack`.
6. **Windows controls** `windows_bdo.py` isolates Ctrl+V and tray operations behind executable verification; tray-icon restoration is best-effort.

## Stability contract

- Keep `GET /durability` backward compatible with the initial working bridge.
- Do not automate mouse/keyboard game actions on OCR updates. Ctrl+V requires a deliberate button click and verified foreground window.
- Do not confuse an HTTP send with a browser acknowledgment.
- Never strip a leading 1 from a legitimate 1xxx reading without strong timer evidence.
- Keep the web app usable without BDO or OCR.

## Known limitations

- Native Windows window/tray integration must be validated on a game PC.
- OCR cannot know which of several similar utensils is active with certainty.
- Auto-scan only reads while BDO is visible, not while native tray mode hides the game.
- The market page includes placeholder/sample market data: do not interpret it as live prices.

## V9 performance and reliability upgrades

- Two-pass-first OCR strategy: stops when two readings agree; capped at six preprocessing/segmentation passes, down from eighteen. Fallbacks only run when results are uncertain.
- OCR history and health status in the main window.
- Deduplicated publishing: unchanged values do not unnecessarily reset the planner; tool changes and periodic heartbeats still transmit.
- Planner maintains the screenshot timestamp and the original `/durability` contract.
- Tray actions remain Windows-only best-effort controls and require confirmation on an actual BDO client.
