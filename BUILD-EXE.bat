@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install --user Pillow pywinauto pyinstaller
if errorlevel 1 (echo Dependencies could not be installed. & pause & exit /b 1)
py -3 -m PyInstaller --onefile --noconsole --clean --name "BDO-Vision-Lite" --icon "%~dp0desktop\assets\bdo-lite.ico" --distpath "%~dp0desktop" --workpath "%TEMP%\BDO-Vision-Lite-Build" --specpath "%TEMP%" --hidden-import=scan_engine --hidden-import=tracking_core --hidden-import=spatial_ocr --hidden-import=ocr_parser --hidden-import=planner_bridge --hidden-import=windows_bdo --hidden-import=comtypes --hidden-import=pywinauto --hidden-import=pywinauto.uia_defines "%~dp0desktop\app.py"
if errorlevel 1 (echo Build failed. & pause & exit /b 1)
echo.
echo Built desktop\BDO-Vision-Lite.exe
 echo Keep the EXE inside the desktop folder, beside the assets folder.
pause
