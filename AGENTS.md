# Development contract

Start with `docs/handbook/01-start.md`, then `python dev.py doctor`.

- User history lives outside this repository. Use `python dev.py run` for a disposable profile. Never reset the real profile to test a feature.
- No automated gameplay. Verify BDO identity and visibility before captures; UI updates belong on Tk's main thread.
- Keep OCR work bounded and below normal priority. A missed read must stay unknown, never become invented loot or a quest completion.
- Preserve `/durability` compatibility, optional sharing, single-instance locking and SQLite-consistent backups.
- Add behavior regressions for OCR decision changes. Use `python dev.py test tool_reader guild_quest` while iterating, then `python dev.py check`.
- Frontend assets and embedded HTML have specific build ownership; see `docs/handbook/08-planner.md`. Check the actual shipped HTML, not only source assets.
- Update the handbook when changing a contract. `python dev.py docs` rebuilds a linked, searchable, offline site and source reference.
- Never publish profiles, game screenshots, diagnostic captures, credentials or personal logs. Preserve published version artifacts; use a new version for changed code.
- Runtime sources: `desktop/` and `bdo-market-intelligence.html`. `native/` is a reader experiment, not a replacement for the production OCR pipeline.
