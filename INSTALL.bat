@echo off
cd /d "%~dp0"
py -3 -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Installing the Pillow screen-image dependency...
  py -3 -m pip install --user Pillow
  if errorlevel 1 (pause & exit /b 1)
)
py -3 install_local.py
if errorlevel 1 (echo Installation could not finish. Existing history is retained. & pause & exit /b 1)
echo BDO Vision is installed. Open the BDO Vision desktop shortcut.
pause
