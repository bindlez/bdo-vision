# Item extraction audit · candidate 1.10.0-rc.3

Tested the released 1.10.0-rc.2 and a parser-fix candidate based on commit bde7747. Findings and fixes are saved on the extraction-audit-1.10 branch. The candidate is not a published or installed release; the current app/profile remain intact while native-reader work is evaluated.

| Check | Released rc.2 | Parser-fix candidate |
| --- | ---: | ---: |
| Declared text cases: 504 positive, 118 negative, 72 mixed | 96 failures / 694 | 0 / 694 |
| Exact bracketed catalog-name preservation | 54 failures / 59,372 valid names | 0 / 59,372 |
| Seeded arriving events with overlap, holes and repeated frames | 2,000 counted once | 2,000 counted once |
| Duplicate/empty-frame events in that simulation | 0 | 0 |
| Independently labeled real rows: eight saved frames | 53 / 64 correct | 54 / 64 correct |
| Incorrect accepted events on those labeled rows | 0 | 0 |
| Synthetic altered-font/scale/contrast rows | 11 / 25 correct | 11 / 25 correct |

141 isolated Windows regression tests passed. The real planner and both browser demos pass JavaScript syntax checks. This audit did not run or publish a new native Windows binary.

## Fixed extraction defects

- Decimal, malformed comma groups, multiple counts and huge digit noise could become a smaller count or abort processing. Counts now require a complete, bounded English integer field.
- Mixed feeds could omit acquired/standalone received/obtained/crafting-complete messages because message joining recognized fewer verbs than the parser.
- The xN inside bundle names was mistaken for the drop quantity. Balanced item brackets now define where a quantity can begin, including nested [Event] names.
- Valid names containing Failed or Failure were excluded as failed actions. Item text is now separated from outside status text.
- A harmless leading OCR underscore or trailing quote could hide a readable row. These specific punctuation forms are accepted without accepting extra digits.

## What the numbers mean

The catalog contains 59,373 distinct names. One nonalphabetic placeholder, a single hyphen, is unsupported and excluded. The preservation check uses exact input text with an explicit bracketed name and quantity; it tests parsing and name identity, not pixel recognition, tradability or price availability for every item. Bare popup labels containing an intrinsic xN can be ambiguous; this check does not certify every unbracketed popup form.

All 83 saved frames in one short grind sample were replayed. Eight frames (64 visible rows) were manually labeled independently of OCR. The remaining frames test consistency, not ground-truth accuracy. Most of the remaining labeled misses occur in one moving-background frame where only one OCR pass reads the text clearly; another frame loses colored item text. The reader correctly requires agreement, so it does not fill those gaps with guessed quantities. One additional changed frame was visually inspected to preserve a valid count followed by a stray quote.

The candidate recognized 84.4% of those labeled rows with no incorrect accepted events. This is a small, correlated per-frame sample, not a 100% accuracy claim or a measured session-wide missed-loot percentage. A row missed on one capture can be recovered on a later retained capture; first-frame rows are intentionally a baseline. Fully unseen rows cannot be recovered by these tests.

Five synthetic images with different text scale, slight blur and contrast yielded 11 correct rows out of 25, with no incorrect accepted events. These invented-font stress fixtures expose sensitivity and are not representative gameplay accuracy estimates. They are a useful benchmark for a new reader.

The standard parser microbenchmark was 0.1205 ms versus 0.1271 ms per eight rows (seven rounds of 1,000 parses), approximately 0.0067 ms added. Full OCR median was approximately 0.557 s versus 0.568 s; p95 approximately 1.076 s versus 1.109 s in sequential runs with other machine activity. These timings do not establish a meaningful OCR performance change. Image masks, Tesseract models and pass limits were not changed.

## Market and accounting checks

A disposable ledger confirmed quantity × unit value = 721,200 silver, with 10 recorded units and one unknown item type excluded from the partial value. Normal and rare elixirs remain distinct. Live NA quotes correctly resolved IDs 678, 679 and 9733, including an event-only namesake. An unknown name produced no quote. EU returned an empty list and a single-item HTTP 500, so EU live availability could not be certified; NA prices were not substituted. Region/cache isolation is covered by the regression suite.

## Data, reproducibility and next engine benchmark

Existing screen captures, raw OCR and temporary ledgers stay local under qa-20. No private captures or personal history are committed. The public regression cases are tests/test_extraction_audit.py; run python scripts/run_tests.py and python scripts/check_planner.py. The full local audit harness and reports are retained in qa-20.

A replacement reader should use a larger labeled holdout split by session, background, font and UI scale. Measure accepted-item precision, exact quantity precision, missed-event recall, duplicate counts, p50/p95 capture-to-record delay, whole-process private memory and CPU. Separate image recognition from parser correctness. Keep blocked capture and forecasts separate from observed drops. Do not optimize away rare items or difficult frames just to improve a timing average.
