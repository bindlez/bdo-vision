# 16 · Developer happiness and the next cleanup

## What changed in this development pass

The app now has one development command entry point, disposable launch profiles, targeted isolated test selection, a contributor contract and this generated documentation website. Tool/Quest debugging shares a small reusable viewer instead of duplicating image windows. The site links guides to the actual source, indexes symbols, extracts literal contracts and validates local navigation. None of that tooling runs during ordinary gameplay.

These changes improve edit safety and discovery. They do not claim to have translated, reformatted or split every existing file. A large rewrite alongside OCR changes would make behavior regressions harder to isolate. Keep successful reader behavior traceable while improving the seams around it.

## Whole-repository review

| Area | Finding | Best next change |
| --- | --- | --- |
| Native controller | `app.py` coordinates many unrelated responsibilities | Extract tool-window/controller code unchanged behind a small interface, then test parity |
| Planner delivery | Single HTML plus editable feature assets can diverge | Introduce a deterministic embed manifest with a check-only mode before any wider frontend rewrite |
| OCR decisions | Good rejection boundaries, several reader-specific pipelines | Define small typed observation records at module seams without forcing all readers into one algorithm |
| Settings | Literal dictionaries are easy to extend but hard to audit completely | Centralize defaults and validation one subsystem at a time; test old preference migration |
| Persistence | Durable profile, backups and additive schema exist | Add explicit schema-version bookkeeping before non-additive changes |
| Tests | Broad behavior coverage, some Windows/native coupling | Keep pure domain tests separate from integration fixtures and improve timing determinism |
| Packaging | Safe allowlists and manifests exist | Test that every newly introduced developer entry point and guide is in source bundles |
| Native experiment | Useful prototype, separate from shipped OCR | Add a versioned observation adapter and comparable replay corpus before promotion |
| Documentation | Old release notes sometimes sound current | Keep current handbook authoritative and label historical documents rather than deleting provenance |
| Performance claims | Prior measurements are scoped experiments | Maintain a reproducible benchmark manifest, accuracy labels and comparable environments |

## A practical cleanup sequence

First isolate orchestration from pure policy without changing results. Next centralize named contracts and units. Then consolidate frontend embedding so one source edit always reaches the shipped HTML. After that, profile real hot paths and optimize the measured costs. Only then consider bigger runtime changes. This order improves developer understanding while protecting the user-visible behavior that makes the app valuable.

## Standards for future code

Prefer clear multi-line code for new logic. Keep function arguments explicit and use descriptive units. Separate observed facts, estimates and display strings. Use small pure helpers for domain rules and test real edge cases. Avoid adding a framework for a task the standard library already handles well. Explain why an unusual heuristic is safe, what rejects it and what evidence would justify changing it.

## Maintaining this website

Edit the numbered Markdown chapters. Use relative links to another guide or the actual repository file. `python dev.py docs` regenerates pages, source snapshots, symbol search, schema references and navigation. `--check` validates every generated local link and section anchor. The generator intentionally supports a small Markdown subset: headings, paragraphs, fenced code, flat lists, tables, inline code, bold and links. Raw HTML is escaped. Generated files are not the editable source of truth.

If you change the generator, verify keyboard search, narrow screens, source line links, long code overflow and print layout. Keep it dependency-free and usable from a file URL. Do not make the handbook fetch from the running app or include private QA directories.
