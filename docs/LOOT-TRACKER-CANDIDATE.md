# BDO Vision loot tracker candidate

This build improves automatic UI alignment and lets the primary loot feed continue when the optional rare panel is covered. It retains existing item history, crafting and grind features.

## Install

Download the Windows ZIP, close Vision normally, extract the whole folder and run `OPEN-BDO-VISION.bat`. Do not overwrite a running installation. Tesseract with English remains required separately. Your existing profile remains outside the application folder.

Use Capture Setup to enable Align to saved UI, save BDO's Edit UI layout, and select the intended feed. Keep the selected feed visible. Windows covering the primary feed still pause capture; this build does not read through covering windows. Check the live reader status after switching character, screen resolution, or UI scale.

## Accuracy engine

The source ZIP includes `scripts/benchmark_loot.py` and capture tooling. Follow `docs/handbook/05-ocr.md` for independently labeled replay and JSON reports. The scorer uses production recognition and penalizes incorrect quantities, duplicates and missing events. Private recordings are never included in packages.

## Release status

This is a prerelease. Live 99.7% accuracy has NOT been demonstrated. Automated tests and generated-image replay verify software behavior, not weeks of gameplay reliability. Do not rely on recorded totals as complete until a live comparison has passed. No loot is invented to fill unobserved gaps.
