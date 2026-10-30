# Source history and recovery

Repository: https://github.com/bindlez/bdo-vision

`main` contains versioned source. The first full snapshot is commit `b792235ee555160d2f5706757f8ed899748e5bcd`, the working 1.7.1 baseline. Earlier development is not represented as invented Git history. A local `v1.7.1` tag identifies that baseline.

Before editing, create a named branch. Run `python scripts/generate_assets.py`, `python scripts/run_tests.py` on Windows, and `python scripts/check_planner.py` with Node installed. Commit verified changes. Set matching VERSION and desktop/version.py for each release, and keep its commit with its ZIP/checksum.

`python scripts/package_release.py` builds a source ZIP from an explicit allowlist, generated art/fixtures, a file manifest, Git commit and ZIP checksum. Python, Pillow and Tesseract are required. This is not a standalone EXE. The Windows workflow runs checks and attaches the ZIP as a build artifact. Formal GitHub release publication is separate from build validation.

History and preferences live in `%USERPROFILE%/.bdo-vision`; they are never committed. INSTALL.bat backs up the profile and installed app before updating the desktop shortcut. Reverting source does not erase or revert the loot database.

For app recovery, extract an older verified source ZIP and run INSTALL.bat. Keep the current profile; do not replace it with an older database merely to downgrade code. For database recovery, preserve both current and backup files before choosing a restore point. Never automatically merge overlapping recovered ledgers.

Git excludes captures, diagnostics, databases, preferences, market cache, secrets, build output and ZIPs. Binary artwork stays local and is regenerated from public source for clean releases.
