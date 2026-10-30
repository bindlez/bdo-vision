@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 set "PYTHON=python"
%PYTHON% -m pip install --user -r requirements-optional-tray.txt
if errorlevel 1 (echo Tray support could not be installed. & pause & exit /b 1)
echo Optional tray support installed. Restart BDO Vision Lite.
pause
