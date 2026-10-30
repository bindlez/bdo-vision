# BDO Vision Lite 1.0 · Release check

## Verified in this environment

- Python unit test suite and Python source compilation
- Browser planner JavaScript syntax and headless Chromium simulation
- Localhost bridge GET `/durability`, GET `/health`, GET `/planner`, and POST `/ack`
- Session update, new tool transition, duplicate reduction, and capture timestamp
- OCR parsing of `(350/3000)` and `1,350/3,000`
- Tk main window renders inside its configured dimensions on a virtual display

## Windows verification still required

- Real BDO window OCR at multiple resolutions/UI scales
- Actual Ctrl+V shortcut producing BDO native tray mode with user-specific keybind
- System tray icon detection/activation on target Windows 10 or 11 setup
- Windows executable built with PyInstaller, including logo/resources
- Windows Defender / SmartScreen installer prompts and packaged EXE permissions

Do not claim that simulated Windows API tests confirm native BDO tray entry/exit.
