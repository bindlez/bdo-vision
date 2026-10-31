# Releases, source history and testing

Open **RELEASE-CENTER.bat** in the project folder for the local release library. Windows ZIPs contain the runnable full app; source ZIPs contain editable project files. Every package has an external SHA-256 checksum and an internal per-file manifest with its exact source revision. Release candidates remain labeled until real-world testing supports promotion.

## Source of truth

The canonical repository is https://github.com/bindlez/bdo-vision . `main` is the published release line; `gear-planner` contains the Gear Studio work. Keep changes on focused branches, review the difference, run checks, then commit. Do not replace working app files with an experimental reader. The icon-reader experiment is deliberately outside this release.

Useful commands from the repository, using the development Python:

```
python scripts/run_tests.py
python scripts/check_planner.py
node scripts/test_gear_core.js
python scripts/release_center.py checkpoint known-good-name
python scripts/package_release.py
python scripts/build_windows.py
python scripts/check_windows.py
python scripts/release_center.py refresh
python scripts/release_center.py verify dist/BDO-Vision-VERSION-Windows.zip
```

Checkpoints are annotated Git tags of clean committed source. Existing names cannot be overwritten. They preserve code, not personal databases or captures. GitHub Actions runs the same source tests and packaged-app check on pushes; successful artifacts are downloadable from the run. Keep release versions immutable: fix a candidate under a new version, never silently replace an existing ZIP.

## Recovery without losing history

Keep extracted releases in separate, version-named folders. Close the current Vision before opening another copy. The app uses the same protected `%USERPROFILE%/.bdo-vision` profile and its single-instance lock. Source installation updates already create profile backups, including an SQLite-consistent history copy. Verify the backup exists before any downgrade. Older apps may not support newer profile formats; test with a copied disposable profile first using `BDO_VISION_DATA_DIR`.

Do not reset or restore your live database to change app versions. Database recovery is a separate, explicit operation from source recovery. Never commit profiles, captures, settings or personal history. The release allowlist excludes those files.

## Evidence and limits

`build/test-report.txt` records isolated source regressions. `build/windows-check.json` records the version and result of the extracted executable check, including synthetic OCR. The release center verifies checksums when refreshed; it does no background work. A checksum proves integrity, not that every feature or game frame was recognized correctly. Tesseract English is still a separate requirement for this candidate; the bundled Python runtime does not require a Python installation.
