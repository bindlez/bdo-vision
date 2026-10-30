# BDO Vision · friend test · 1.9.0-rc.1

This is an unsigned Windows test candidate. No Python installation is needed. Extract the whole ZIP before opening **OPEN-BDO-VISION.bat** or **desktop/BDO-Vision.exe**. Keep the accompanying folders beside the EXE.

## Real game OCR

1. Install Tesseract with English once if it is not already installed. The official project links Windows installers here: https://tesseract-ocr.github.io/tessdoc/Installation.html . Vision expects `C:\Program Files\Tesseract-OCR\tesseract.exe`; another location can be entered in Settings.
2. Open BDO and show the personal **You have obtained…** message panel with 6–8 complete rows. Keep item names and quantities fully visible.
3. Open **Silver & Loot History → Capture Setup**, choose **Text feed**, select that message panel, then enable **Tracking ON** and **Record loot**. Use only one loot feed at a time.
4. Return to the game. In Vision’s Grind tab, name the spot and start a run. Optional sharing connects recorded results to the local planner.
5. For a useful comparison, start a second tracker at the same moment. Compare item quantities first, then prices and total silver. Blocked text, lost scrolling overlap and uncertain quantities can still miss loot; this candidate does not infer missing items.

Silver is captured quantity × matching market or verified NPC value, before costs and fees. Items without a verified price remain excluded from a labeled partial total. Initial market matching needs an internet connection.

## History and recovery

The app saves history on your own PC in `%USERPROFILE%/.bdo-vision`, separate from the extracted ZIP. Reopening a copy restores the existing instance. Starting a new session keeps older records. Startup creates a verified history backup. The package contains no developer/user loot history, settings or screen captures.

Please report the version, scan time/capture gap, one clearly missed item and both tracker counts for the same run. Do not send account credentials. Record any capture outages separately.

## Browser demo

The browser demo uses simulated drops and fixed example prices. It demonstrates session timing, capture pauses and valuation. Native screen capture, tray restoration and global shortcuts require the Windows application.
