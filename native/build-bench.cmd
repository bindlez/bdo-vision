@echo off
setlocal
if defined VSCMD_VER goto compiler_ready
set "VISION_VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VISION_VSWHERE%" exit /b 1
for /f "usebackq tokens=*" %%i in (`"%VISION_VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VISION_VS=%%i"
call "%VISION_VS%\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
:compiler_ready
if not exist build\native\items.bin (
 echo Generate build\native\items.bin with native\generate_catalog.py first.
 exit /b 1
)
>build\native\catalog.rc echo 101 RCDATA "items.bin"
rc /nologo /fo build\native\catalog.res build\native\catalog.rc
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /utf-8 /O2 /GL /MT /EHsc /W4 /DUNICODE /D_UNICODE native\reader_bench.cpp build\native\catalog.res /Fo:build\native\reader_bench.obj /Fe:build\native\bdo-native-bench.exe /link /LTCG /OPT:REF /OPT:ICF
if errorlevel 1 exit /b 1
if "%~1"=="--tests-only" goto self_test
cl /nologo /std:c++20 /utf-8 /O2 /GL /MT /EHsc /W4 /DUNICODE /D_UNICODE native\preview.cpp build\native\catalog.res /Fo:build\native\preview.obj /Fe:build\native\BDO-Vision-Native-Lab-01.exe /link /SUBSYSTEM:WINDOWS /LTCG /OPT:REF /OPT:ICF
if errorlevel 1 exit /b 1
dumpbin /nologo /dependents build\native\BDO-Vision-Native-Lab-01.exe > build\native\imports.txt
:self_test
cl /nologo /std:c++20 /utf-8 /O2 /GL /MT /EHsc /W4 /DUNICODE /D_UNICODE native\self_test.cpp build\native\catalog.res /Fo:build\native\self_test.obj /Fe:build\native\native-self-test.exe /link /LTCG /OPT:REF /OPT:ICF
if errorlevel 1 exit /b 1
build\native\native-self-test.exe
