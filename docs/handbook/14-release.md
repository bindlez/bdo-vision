# 14 · Git, packaging, releases and recovery

## Source identity

The canonical repository is [bindlez/bdo-vision](https://github.com/bindlez/bdo-vision). The first stable release is [v1.12.0](https://github.com/bindlez/bdo-vision/releases/tag/v1.12.0). At that release, `gear-planner` was the active release branch. Older documents describing only `main` are historical; inspect the current workflow before assuming a branch will publish.

Use focused branches, small meaningful commits and reviewable diffs. Commit code and tests together when they define one behavior. Keep documentation contracts in step with changes. A checkpoint is an annotated tag of clean source; it is not a history backup. Never force-update a published version tag or silently replace its ZIP.

## Versioned workflow

Update both `VERSION` and `desktop/version.py` when making a new candidate. Prepare changelog/release notes describing the actual final behavior and remaining limitations. Run `python dev.py check`, inspect the report, then build source and Windows packages. A local package records source identity and whether source was dirty. For a final reproducible package, commit first and validate that exact source.

```powershell
python dev.py check
python scripts/release_center.py checkpoint YOUR-NEW-CHECKPOINT
python scripts/package_release.py
python scripts/build_windows.py
python scripts/check_windows.py
python scripts/release_center.py refresh
python scripts/release_center.py verify dist/BDO-Vision-YOUR-VERSION-Windows.zip
```

Do not type a published version into a builder and overwrite an old local package. Use a new candidate identity. `requirements.txt` is the runtime dependency list; PyInstaller and tray integration dependencies are build/distribution concerns. See [build_windows.py](../../scripts/build_windows.py) for the exact staging rules.

## GitHub Actions

The workflow runs on pushes, pull requests and manual dispatch. It installs Python/Node/Tesseract, generates safe assets, runs tests, builds both packages and validates the extracted app. Artifacts are available from the run. The `first_release` job is intentionally restricted to version 1.12.0 on `gear-planner`; it preserves an existing release. It will not automatically publish an arbitrary later stable version. The separate prerelease job has its own branch/version conditions. Read the actual YAML before changing publication behavior.

## Package contents and privacy

Source packaging uses an explicit allowlist. Branding and OCR test fixtures are generated safely; live captures and user databases are excluded. The Windows release bundles the application/runtime and includes integrity metadata. SHA-256 verifies downloaded bytes, not recognition quality or code signing. The app is not made signed merely by running the build.

The handbook is a separate developer artifact under `build/developer-handbook`. Its source is included through the documented source allowlist; the source bundle can rebuild the site. It does not load in the background during gameplay.

## Installing and rolling back

Close the running Vision normally. Acquire its single-instance guard before installing, create a verified profile backup, replace application files, verify history, then reopen. Do not force-kill or overwrite loaded modules. If a file lock prevents the update, preserve the candidate and finish after the app closes.

To roll back code, test an older release against a copied development profile first. Newer schema or browser state may not be backward-compatible. Never restore an older database merely to return to an older executable. If recovery of data is required, preserve the current profile and perform it as a separate explicit operation.
