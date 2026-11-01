@echo off
cd /d "%~dp0"
python scripts\build_handbook.py
if errorlevel 1 (
  echo Handbook build failed. See docs\handbook\01-start.md for setup.
  pause
  exit /b 1
)
start "" "%~dp0build\developer-handbook\index.html"
