@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=py -3"
py -3 --version >nul 2>nul
if errorlevel 1 (
  set "PYTHON=python"
  python --version >nul 2>nul
  if errorlevel 1 (
    echo Python 3 was not found. Please install Python 3 and try again.
    pause
    exit /b 1
  )
)
%PYTHON% -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo Installing the screen-capture dependency Pillow...
  %PYTHON% -m pip install --user Pillow
  if errorlevel 1 (echo Pillow installation failed. & pause & exit /b 1)
)
if exist "..\scripts\generate_assets.py" %PYTHON% "..\scripts\generate_assets.py"
%PYTHON% app.py
if errorlevel 1 (echo BDO Vision closed with an error. & pause & exit /b 1)
