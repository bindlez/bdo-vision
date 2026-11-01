# 10 · Local bridge and security contracts

## API shape

The bridge binds loopback and serves the paired planner. Port 7288 is the familiar local address but is not a universal guarantee. Inspect `/health` and the current profile's runtime status to identify the instance. The bridge is a local integration service, not a ready-made public backend. Do not expose it to a LAN or put it behind a public tunnel without a separate authentication design.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/`, `/planner` | Shipped planner HTML |
| GET | `/health` | App/bridge identity, version, process and synchronization status |
| GET | `/durability` | Backward-compatible craft signal, optional shared loot and snapshots |
| GET | `/tool-reader` | Bounded tool status; no debug screenshots |
| GET | `/guild-quest` | Last-seen quest status; no projected credit |
| GET | `/prices` | Cached price-book summary |
| GET | `/timer-earnings` | Scoped earnings; requires optional sharing and matching history identity |
| GET | `/grind-session` | Shared grind session detail |
| GET | `/gear/extras`, `/gear/builds`, `/gear/sweep` | Extra equipment identities, backups and job polling |
| POST | `/ack` | Acknowledge a valid signal for the current instance |
| POST | `/show` | Request native window restoration for the current instance |
| POST | `/market-prices`, `/craft-quotes` | Import validated quotes or fetch recipe quotes |
| POST | `/grind-command` | Queue a bounded start/pause/finish request |
| POST | `/gear/ocr`, `/gear/sweep`, `/gear/builds` | On-demand equipment recognition and validated build backup |

The exact request validation and response fields are in [planner_bridge.py](../../desktop/planner_bridge.py). The generated contracts page lists literal route names extracted from the current source. The table is a navigation guide, not a promise that every route accepts arbitrary JSON.

## Request validation

POST handlers require an allowed origin and JSON content type. Bodies have route-specific byte limits: equipment images have a larger bound than acknowledgments. Ambiguous content lengths, transfer encoding, unexpected content encoding, non-finite JSON numbers and non-object JSON are rejected. Preserve all these checks when adding a route.

Instance IDs protect synchronization against confusing two running sessions; they are not user account authentication. Acknowledgments must reference a known positive signal. Grind actions are limited to known commands and a bounded queue. Gear jobs use a nonblocking gate and return busy status rather than spawning unlimited readers.

## Concurrency and responses

Copy shared state under the bridge lock. Do not return a mutable internal object that a later update can change while it is being serialized. HTTP handlers cannot directly mutate Tk widgets or use the UI-owned SQLite connection. Queue a request and let the main controller apply it safely.

Use meaningful errors: invalid input is different from an unavailable recognizer, stale history, disabled sharing or a busy job. The browser should preserve its last valid data and explain the condition instead of replacing it with a misleading zero.

## Security maintenance checklist

Use fixed command argument lists for OCR; never pass recognized text into a shell. Bound decoded image dimensions as well as request bytes. Treat all market/OCR strings as text in the browser. Keep private captures and profile paths out of public artifacts. Test foreign origins, oversized bodies, malformed JSON, stale signals and malicious display strings. See [the security tests](../../tests/test_bridge_security.py) and [rendering tests](../../scripts/test_planner_security.js).
