# Vision Idea Desk

Open `demo/vision-idea-desk.html` in a browser. This standalone sideapp needs no
server, installation, account, external library or Vision connection. Keep using
the same browser and file location: local browser storage is not a portable file.
Use **Back up notes** regularly; browser clearing/private mode can lose local data.

1. Capture a thought as an Idea, Problem, Task or Fix. Ctrl+Enter captures it;
   Ctrl+K focuses capture. New notes enter Inbox and are included in the next brief.
2. Open a card to add evidence, reproduction steps, success criteria, area, priority
   and workflow state. Save changes explicitly. Completed/Parked notes are retained
   but excluded from prompt generation.
3. Check the notes to include. Add the main outcome, context and preservation rules.
4. Assemble, review and edit the brief; copy it or download Markdown for our chat.
   The app formats a draft; it does not call an LLM or claim to reason about notes.
5. JSON imports merge by stable ID, choosing the newer edit. Existing nonempty
   prompt settings are preserved; blank ones restore from backup. No bulk erase.

Storage failures keep the current in-memory workspace exportable and pause writes.
Conflicting tabs also pause writes: export the conflicting tab, reopen the main
copy and import its backup to merge. Imported files are validated before changing
the workspace. Personal notes never enter the Git repository or Vision profile.

Sources are here; run `python scripts/build_idea_desk.py` to regenerate the single
HTML artifact, then `node scripts/test_idea_desk.js` to check core behavior and bundle
syntax. This sideapp changes no Vision runtime or OCR behavior.
