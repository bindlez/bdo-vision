# BDO Vision · ready to grind and craft

Extract the entire Windows ZIP. Close any older Vision, then double-click **OPEN-BDO-VISION.bat**. Keep the folders beside the EXE. Python is included; Tesseract English is still required for OCR. Existing users keep the same protected history and settings.

## Start a grind

1. Open **Silver & Loot History → Capture Setup**. Choose **Text feed** and select only BDO's personal **You have obtained…** messages. Show 6–8 complete rows, including item names and quantities. Keep this area uncovered.
2. Turn on **Tracking ON** and **Record loot**. Leave **Crafting mode** off. Start at a 2-second loot interval; try 1 second if your feed scrolls too quickly. The first readable text frame establishes a baseline of existing messages.
3. Wait for an identified reading, then open **Grind**, name your spot and start the session before fighting. After a restart, resume an unfinished session explicitly.
4. Check **Silver** for observed item value and price coverage. Unpriced items stay recorded but are excluded from partial silver totals. Capture outages pause observed time; missing drops are never invented.

Minimize Vision while playing, leaving the game and selected loot area visible. Tool OCR stays idle during grinding when no tool timer is running. Loot recording continues independently of the open tab.

## Start crafting

Enable **Crafting mode** in Capture Setup before the run. Keep the same personal loot feed visible and let it establish a baseline. For session grouping, use **Sessions**. For recipes, input costs and planning timers, optionally enable **Share recorded loot with planner**, then open the planner from Vision. Open the paired localhost page rather than an old standalone HTML copy.

Recorded silver is captured quantity × market/NPC unit value before costs and fees. The crafting planner labels modeled costs/net separately. Crafting projections while capture is blocked are optional estimates; they never become saved loot. Native OCR cannot see BDO while the game is in its tray.

## If a reading stops

Move covering windows away, return to BDO and check the **OCR reader** tab. Your capture area may need adjusting after a resolution/UI-scale change. Save diagnostic images only when troubleshooting: enable that checkbox in Capture Setup, reproduce the issue, then open OCR diagnostics. Normal recording does not write screenshots to disk.

Your history remains in `%USERPROFILE%/.bdo-vision`. Use the app's history backup and CSV export before major changes. Never replace the live database with an older one just to switch app versions. Gear Studio's reviewed tooltip import remains available; icon-only import is still experimental.

## Automatic durability

No box is needed for cooking/alchemy tool durability. Keep BDO in front with tool labels visible. Open NEARBY TOOLS to inspect what was read. The reader confirms active use after two separate decreases and reacquires after camera motion. If labels leave the screen, measurements wait until they are visible again. Existing manual area selection is optional.
