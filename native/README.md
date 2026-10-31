# Native reader lab

Product goal: one Windows executable, no separate Python/Tesseract/model-runtime installation, very low idle CPU/private memory, and measured item/quantity accuracy. A native benchmark will be compared to the frozen saved-frame corpus. The existing released app and protected profile remain available. No native preview will write to the production ledger until parity is demonstrated.

Stage 1: Windows-only image loading/capture, bounded buffers, custom glyph recognition, replay metrics and import/dependency audit. Stage 2: temporal extraction and exact item identities. Stage 3: protected history, market/website bridge, tray and native UI. Stage 4: same-workload comparison against the previous build and other trackers before making any comparative leanest claim.

Build dependencies are confined to development (MSVC and Windows SDK). The shipped executable will statically link its C/C++ runtime and use Windows system APIs. Recognition data must be embedded or generated locally; no fonts or personal game captures will be published.

## Lab 01: what is usable now

`BDO-Vision-Native-Lab-01.exe` is a standalone, read-only Windows preview. Open an existing image, or select only the system text feed (include “You have obtained”), click Start, and bring BDO to the front. Escape cancels area selection. The preview checks the foreground game and five points of the capture area before reading. It suspends when those checks fail. Capture buffers are reused and the worker sleeps when paused. Recognition caches have fixed limits.

Visible rows are **not session totals**. The preview has no ledger writes, price queries, website bridge, tray integration, forecasts or production-profile access. It does not replace the released app. Small covering windows between the five test points are not detected; the header/recognition checks still apply. Live capture and area selection require further testing in-game. Only English, single-line system text is currently supported. Wrapped feeds, other fonts/scales and implicit-one rare drops need more validation.

The custom reader renders Windows fonts locally. It embeds the public item-name catalog and statically links its C++ runtime. No game fonts, model runtimes, Python, Tesseract or installers are required by the preview. Item names alone do not establish a tradable market ID.

## Build and replay

Run these from the repository root in a development environment with Python, MSVC C++ tools and Windows SDK. These are build tools, not end-user requirements.

```text
python native/generate_catalog.py --catalog PATH_TO_PUBLIC_CATALOG.sqlite3 --output build/native/items.bin
native\build-bench.cmd
build\native\native-self-test.exe
build\native\bdo-native-bench.exe --image PRIVATE_CAPTURE.png --ensemble --repeat 20
build\native\bdo-native-bench.exe --sequence PRIVATE_CAPTURE_DIRECTORY
python native/evaluate.py --exe build/native/bdo-native-bench.exe --frames PRIVATE_DIRECTORY --labels PRIVATE_LABELS.json --output PRIVATE_REPORT.json
```

Catalog JSON input is also supported: a list of objects with a `name` string. The SQLite input expects `catalog_items(name)`. The builder locates Visual Studio through `vswhere`. `--tests-only` skips rebuilding the interactive executable while it is open. The import audit is in `build/native/imports.txt`. `--smoke IMAGE` runs the GUI recognition path invisibly, prints resource measurements, then exits; `--image IMAGE` opens the preview with a saved image.

See [the measured checkpoint and remaining gates](../docs/NATIVE-READER-LAB.md). Saved images, labels, binary resources and reports remain outside versioned source. The labels runner supports empty expected lists for negative images. A development set and a separate recording are both needed; the existing small sample cannot establish general OCR accuracy.
