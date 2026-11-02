# Verified delivery · 1.13.0-rc.13

November 2, 2026. Runtime source was committed before testing and packaging. Earlier
release artifacts and immutable checkpoints remain intact. Later documentation
updates do not change these packages or move their checkpoint.

## Source identity

- Local package commit: `928475b89158f7b4c3e33ccd50250670420a3d84`.
- Identical public source tree: `2c1c599e574bf10601e357f62ffd262472710b37`.
- [Public source checkpoint](https://github.com/bindlez/bdo-vision/commit/85715b48a2402a558a05f3f1d93c4a057f262391).
- [Windows CI passed](https://github.com/bindlez/bdo-vision/actions/runs/41540433650).
- Local immutable tag: `checkpoint/1.13.0-rc.13`.

The locally packaged and API-backed public commits have different commit metadata
but exactly the same source tree. The archive manifests identify the local commit.

## Checks and artifacts

379 Python tests passed with no failed modules. Actual shipped HTML syntax, Gear,
rendering safety, Big Drops, CP parity/page interaction, Crafting catalog/page
interaction, compilation and handbook-link checks passed. The packaged handbook
contains 54 guides, 167 source pages and 1,946 search entries.

The extracted Windows executable passed native widgets, CP widgets/example,
history integrity, bridge and synthetic OCR checks. The installation check passed
again with system Python omitted from PATH. Tesseract English is still an external
runtime requirement; this is not a claim of dependency freedom.

| Artifact | SHA-256 |
| --- | --- |
| BDO-Vision-1.13.0-rc.13-Windows.zip | a2940b70c584d05b3e9c4d297204f34d2fe37c9f602ebaee2355e6924fe3768b |
| BDO-Vision-1.13.0-rc.13-Windows-Source.zip | d8e65f8d1131aa77d118e8b135be5f00ea0db6a96e82e93f99f863dd8da8eb3a |
| Developer-Handbook-1.13.0-rc.13.zip | fa1cf09e75faa86743f50bd96769cabc76c4970ed0ccfe6cf1f4325bf8bc113a |

The standalone update was installed after a normal close. A consistent backup was
verified; the complete database logical hash matched before/after installation.
Exact private history counts, backup paths and hashes are retained privately, not
published here. The desktop shortcut points to the new standalone executable;
previous version directories remain available.

The reopened app's health API confirmed rc.13. Its served planner contained all
990 recipes. A guarded installed-app lookup refreshed all 11 CP reward quotes by
exact ID. History integrity remained `ok`, and subsequent recording continued.

## Public delivery

- [Crafting Intelligence demo](https://bindlez.github.io/bdo-vision-crafting-demo.html).
- [Market-first CP Intelligence demo](https://bindlez.github.io/bdo-vision-cp-demo.html).
- [Project engineering paper](https://bindlez.github.io/bdo-vision-project-paper.html).
- [Editable paper Markdown](https://bindlez.github.io/bdo-vision-project-paper.md).
- [Project index](https://bindlez.github.io/).
- [Pages publication commit](https://github.com/bindlez/bindlez.github.io/commit/16e33a33a7831a9870fa44b13e6ceb35b60c7cbb).
- [Successful Pages deployment](https://github.com/bindlez/bindlez.github.io/actions/runs/41541027723).

All four published files returned HTTP 200 and matched the checked local text
after Windows/LF newline normalization. The index contains the new links. The
public demo has dated prices and simulated drops; native game OCR remains local.

## Scope and remaining manual acceptance

The [reference matrix](CRAFTING-REFERENCE-MATRIX.md) records supported functions
and explicit exclusions. No authenticated reference-site workflows or proprietary
implementation were copied. Custom item-price editors remain omitted by request.
Absent minimum-skill facts and unavailable prices stay explicit.

Desktop input/focus interruptions prevented a reliable final visual browser pass;
the reopened native window also reported minimized. API, DOM and package checks
do not substitute for fresh visual inspection or an in-game accuracy study. No
claim of perfect OCR, zero FPS impact or every-layout visual validation is made.
