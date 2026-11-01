# 17 · Equipment import and Gear Studio

## Separate identity, enhancement and stats

The market catalog provides item identities and enhancement-specific quotes. It is not a verified AP/DP progression database. Gear Studio can edit equipped/target builds and calculate upgrade costs without claiming complete combat-stat simulation. Non-market equipment may resolve through the local extras index; that does not make a Central Market quote exist for it.

`gear_catalog.py` supplies extra equipment identities. `gear_ocr.py` validates the supplied equipment catalog, normalizes names, recognizes enhancement prefixes/ranks and rejects uncertain matches. Slot assignment belongs to reviewed build state, not arbitrary OCR guessing. Accessories need distinct slot identities even when they have the same item name.

## Tooltip sweep lifecycle

The import is explicitly user-triggered. `gear_sweep.py` gives a lead-in, verifies BDO, then samples bounded crops while the user moves over equipment. It collects at most twelve short-lived grayscale crops during the sweep. Tooltips near screen edges need a crop that retains the header; pointer position alone is not a complete tooltip rectangle.

Recognition happens after capture. Foreground loss cancels or truncates the operation rather than capturing unrelated windows. Jobs are guarded so repeated requests cannot create an unbounded queue of OCR work. The bridge exposes a job ID/stage for polling. Users review imported identities, levels and slots before applying the build.

## Icon-only recognition

The earlier icon-reader/native experiments are not a guarantee that every item can be identified from its equipment icon alone. Similar icons, tiny enhancement glyphs, scaling and overlays are ambiguous. Keep unknown identity or enhancement explicit and preserve the tooltip review route. Do not claim a screenshot of a gear panel proves full automatic import accuracy.

## State and backup

The browser owns editable equipped/target sets and named builds. `gear_store.py` validates and backs up build JSON to the Windows profile, retaining the previous copy. Imports must be sanitized before replacing state. Unknown fields, invalid slot contents, impossible levels and oversized structures should fail safely. A JSON export remains useful when the bridge is offline.

## Editing the feature

Change recognition rules in Python and add `test_gear` cases. Change slot/enhancement rules in the JS core and run `node scripts/test_gear_core.js`. Change rendering in the gear assets, run `python scripts/build_gear.py`, then check the actual planner HTML. Test offline quotes, unlisted equipment, duplicate rings, invalid imports and a failed backup as well as a normal build.

For a future public backend, keep account authentication, ownership and cloud synchronization separate from this local bridge. [The backend plan](../BACKEND-PLAN.md) is planning material, not an existing authenticated service.
