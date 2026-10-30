# Crafting Studio and efficiency review · 1.10.0-rc.2

The release adds planning and separate, opt-in blocked-capture projections without changing the OCR consensus, quantities, overlap handling or loot ledger. Existing recipes are retained; this is not a newly verified comprehensive recipe or mastery database.

## What changed

- Central Market resolves selected recipe outputs and ingredients by exact identity and region. Ambiguous names are excluded; bundled fallback values stay visibly labeled. Recipe lookups are on demand, limited to 64 names, with a five-minute, 16-request cache. There is no second editable price book.
- Plans include expected main yield, seconds per batch, sale proceeds retained, extra cost per batch, inventory, buy/make intermediates, shared ingredient shopping, ordered production steps, break-even price and profit/hour. Comparison ranks fully matched plans before assumptions. Owned materials reduce shopping cash but still carry economic value. Group ingredients retain their existing definitions rather than being assigned a guessed item.
- Up to 100 saved production plans, shopping-list export, and plan/assumption backup. Plans are local to this browser origin; export before changing ports or browsers. The production queue is a planning list; it does not control the game. Intermediate recipes must be started in their displayed order.
- Active recipe timers filter captured events to crafting kinds. Recorded gross value stays separate from modeled input cost/net. The cost model is main captured quantity / assumed yield × locked input cost per batch; consumption is not directly measured, and rare-only batches can be incomplete. Configured sale retention applies to recorded gross for the modeled net. Region changes make incompatible net comparisons unavailable.
- Opt-in blocked forecast applies only to cooking/alchemy, native Crafting mode, a running timer and a fresh bridge reporting a covered/minimized/tray window. It projects main items and gross value for the current gap only, from configured speed/yield. It resets on recovery and stops on stale connection, mode change or timer end. It never changes the ledger, rate denominator, confirmed totals, rare loot, or grinding. Continued game crafting is an assumption; the game may stop before the timer.
- Small SVG cumulative value graph, input/proceeds bars, item contribution and a user-set recorded-silver goal. Native Silver has top-item bars and milestone progress. No chart dependency, font download, particle effects or permanent animation loop. Maximum 48 graph points. Reduced motion is respected.

## Measured comparison

Windows Python 3.14, baseline Git 2e727b4 (1.9.0-rc.1), candidate working source. Synthetic 100,000-event, one-item ledger; five timer samples using tracemalloc. Both produce 100,000 events, 250,000 units and 25,000,000 silver.

| Measurement | Baseline | Candidate |
| --- | ---: | ---: |
| Timer valuation median | 649.88 ms | 138.74 ms |
| Timer query peak Python allocations | 34,943,328 bytes | 5,249 bytes |
| Warm unchanged price snapshot median, 30 samples | 23.756 ms uncached | 0.0006 ms cached |
| Same-history app private memory, hidden capture/network idle | 42,786,816 bytes | 43,503,616 bytes |

The timer query is about 78.7% faster in this specific large-history fixture. The allocation figure excludes SQLite native allocations, OCR child processes and browser memory; it is not total application RAM. The app measurement is one paired run: about 0.68 MiB more private memory, not a memory reduction. New cached snapshots trade a small bounded residency cost for less repeated work. No new native/runtime dependencies were added. Earlier 1.9 catalog/mask results remain separately documented in PERFORMANCE-RC1.md.

## Where the time and memory went

1. Timer earnings fetched every event into Python. SQLite now aggregates by item/kind and retrieves only the latest 12 events; observed/excluded time uses the same span calculation. Memory grows with distinct item types, rather than event count.
2. Every native share tick queried full history twice and revalued it. Summary caching now keys on ledger changes and price snapshot changes, with immediate invalidation on quote updates. Capture state/clock still update live.
3. Native prices repeatedly loaded and matched identical quotes. A two-second snapshot cache picks up other connections, and own writes invalidate immediately. Unchanged snapshots retain their identity. Only a small bounded number of region snapshots are held.
4. The website rebuilt timer cards four times per second. It now updates once per second while the craft view is visible. Bridge reads are two seconds for visible activity, eight seconds while browsing the market, and fifteen-second backoff when disconnected. Hidden tabs stop bridge requests and catch up on visibility. Browser throttling is expected; recorded native history continues independently.
5. Standalone HTML rediscovered all ten bridge ports even after connection. It now reuses the working origin and discovers again only after failure. Unchanged loot item arrays are omitted from bridge responses and retained by the website. Full initial responses remain compatible with older planners.
6. Empty market POSTs no longer rewrite the cache every five seconds. The large legacy screenshot OCR script loads only after an explicit browser OCR action. Windows OCR is unchanged.
7. Tool-timer refreshes no longer replace the selected recipe or rebuild its focused planning controls. Large timer chunk arrays are capped at 256; saved production plans can hold additional work.

## Deeper audit: next candidates, in order

- Closed grind sessions: summaries repeatedly traverse completed session rows and frozen quotes. Cache immutable finished summaries with explicit invalidation for late rare-kind updates; measure with hundreds of sessions before changing the membership path.
- Native aggregate history: Silver/history views still traverse rows on new loot. Add SQL aggregates and paged event browsing with canonical identity parity tests. Avoid a permanently resident full-history list.
- OCR diagnostic writes: last_capture.png and text diagnostics are rewritten per scan. Consider a bounded diagnostic cadence plus immediate failure snapshots, while preserving current Live OCR debugging.
- Tesseract launch/PNG encode: separate subprocess startup, masking, encoding and recognition timings on a labeled live replay corpus. A resident native model can reduce latency but increases idle RAM; do not adopt it just because a microbenchmark is faster.
- Static-frame reuse: only reuse a fully verified unchanged text mask. Moving scenery and unreadable rows can hide new messages; measure missed-event recall before adding a skip rule.
- Recipe confidence: verify ingredient groups, allowed substitutions, rare output identities and mastery yield curves against authoritative data. Do not imply a default 1-item yield or bundled fallback is a verified character-specific rate.
- Front-end data: bound market name maps to loaded categories/region, and move historical research tables to lazy/paged views if actual browser profiles show them dominating. Do not migrate to a framework merely for charts.

## Accuracy and release checks

128 isolated Windows regressions cover existing OCR, tray, history, exact market matching, timer spans and new crafting math/forecast boundaries. Additional checks include inline-script syntax for the real planner and both demos, actual browser interactions, generated fixture OCR in the packaged EXE and release manifest checks. The UI demo explicitly uses synthetic prices/drops and blocks all network connections through its policy. Screen OCR is only in the Windows app. Perfect live OCR recall is not established by these checks; covered or lost feed rows remain unrecorded.
