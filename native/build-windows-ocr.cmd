@echo off
setlocal
if defined VSCMD_VER goto compiler_ready
set "VISION_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VISION_VSWHERE%" exit /b 1
for /f "usebackq tokens=*" %%i in (`"%VISION_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VISION_VS=%%i"
call "%VISION_VS%\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
:compiler_ready
if not exist build\native mkdir build\native
cl /nologo /std:c++20 /utf-8 /O2 /MT /EHsc /W4 /DUNICODE /D_UNICODE native\windows_ocr_worker.cpp /Fo:build\native\windows_ocr_worker.obj /Fe:build\native\vision-windows-ocr.exe /link /OPT:REF /OPT:ICF
exit /b %errorlevel%
