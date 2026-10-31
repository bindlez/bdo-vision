# Lean backend plan

A Cloudflare Worker can be the backend API; D1 can store accounts' gear builds and optional session summaries. The existing GitHub Pages site can remain the frontend. No always-running VM, framework server, remote OCR or live screenshot upload is needed for the initial product.

## Staged rollout

1. Keep current planning local and optional Windows backups. Store compact, versioned build JSON with exact item IDs and enhancement levels, not copies of the entire catalog. Preserve the no-account path.
2. Deploy a small Worker for `/v1/builds` and a shared market cache. Cache public catalog/quote requests by region + item ID + enhancement interval. Validate upstream data and use bounded TTLs; no live push stream is necessary.
3. Add authenticated personal sync with D1. Use a real identity provider/session flow; a Worker URL or client-side API key is not authentication. Verify owner access on every build query. Use indexed owner/build keys, request size/rate limits, revision-based conflict handling and prior build versions. Keep all credentials out of GitHub Pages source.
4. Add explicit share links with random, revocable tokens for selected builds. Private builds stay private by default. Session summary upload remains opt-in, independent of loot capture.

Suggested schema:

```sql
CREATE TABLE gear_builds (
  owner_id TEXT NOT NULL,
  build_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, build_id)
);
CREATE TABLE gear_build_versions (
  owner_id TEXT NOT NULL,
  build_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  payload TEXT NOT NULL,
  saved_at TEXT NOT NULL,
  PRIMARY KEY (owner_id, build_id, revision)
);
```

Retain a bounded version history and require `expected_revision` on writes to prevent an old browser from overwriting a newer build. Never put game screenshots, profile paths, raw loot history or credentials into public share payloads. Sync on edit/explicit save with a debounce, not continuous polling. OCR, game access and global/tray controls remain on Windows.

Deployment is not configured or claimed in this change: no Cloudflare account/Worker binding is connected to this repository. Before deployment, choose the identity provider, configure the user's Worker/D1 account and bindings, set allowed frontend origins, and verify restore/export paths. No paid services have been provisioned.

References checked 2026-10-30: [D1 overview](https://developers.cloudflare.com/d1/), [Worker D1 binding API](https://developers.cloudflare.com/d1/worker-api/), [Workers pricing and limits](https://developers.cloudflare.com/workers/platform/pricing/), [D1 limits](https://developers.cloudflare.com/d1/platform/limits/). Recheck current quotas against actual usage when deploying; no “free forever” assumption is built into the app.
