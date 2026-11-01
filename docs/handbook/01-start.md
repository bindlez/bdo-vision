# 01 · Start here

This handbook describes the app that exists in this checkout. BDO Vision combines a Python/Tk Windows desktop app, local SQLite history, a local HTTP bridge and a browser planner. Python orchestrates capture and recognition; Tesseract performs production OCR. Pillow handles images. The C++ reader is an experiment, not the production recognizer. A Windows ZIP bundles Python but currently still requires Tesseract English separately. Do not advertise it as dependency-free.

## Your first safe edit

Install Python 3.12 or later on Windows, Git, Node and Tesseract English. Python 3.12 is the CI baseline; later Python versions need their own package checks. Open a terminal in the repository. The commands below use your chosen Python environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python scripts/generate_assets.py
python dev.py doctor
python dev.py run
```

`dev.py run` launches a disposable development profile. It does not load your real loot history, starts automatic readers disabled and removes the disposable profile when the process exits. The development bridge may choose another available port if the installed app is also open. Follow the address shown by that app, rather than assuming every test instance owns port 7288.

For a persistent sandbox use `python dev.py run --profile build/my-dev-profile`. The launcher refuses the normal live profile and its descendants. Do not use production history as a sandbox. The installed app and direct `RUN.bat` launch use the normal protected profile; they are not substitutes for this development command.

## First navigation route

Read [the architecture](02-architecture.md), then [the editing map](03-editing-map.md). If changing recognition, read [OCR contracts](05-ocr.md) before editing. If changing silver calculations, read [valuation](09-economy.md). Finish every behavior change with [testing](11-testing.md), and follow [release and recovery](14-release.md) before packaging.

## What the developer commands do

| Command | Result |
| --- | --- |
| `python dev.py doctor` | Read-only report of interpreter, dependency presence, version and Git status. It does not install anything. |
| `python dev.py run` | Native app using a temporary profile. Close it normally when finished. |
| `python dev.py test` | All Python regression modules, isolated per module. |
| `python dev.py test tool_reader guild_quest` | Only those modules, still isolated. |
| `python dev.py check` | Full Python tests, actual planner JavaScript, gear rules, rendering safety, compilation and handbook links. |
| `python dev.py docs` | Build this offline website, search index and line-linked source atlas. |

No Node package installation or web server is needed for this handbook. Open `build/developer-handbook/index.html`. The launcher `DEVELOPER-HANDBOOK.bat` builds and opens it. The website is generated: edit the Markdown under `docs/handbook`, not the output HTML.

## Start with a reversible change

Try changing one label in [the tool window](../../desktop/app.py), then run with a disposable profile. Compare the visual result, check keyboard focus and restore the label. This exercises your environment without changing game capture or history. For an actual contribution, work on a focused branch and inspect `git diff` before committing.
