# Gear Studio — full-app candidate 1.11.0-rc.1

Gear Studio is added to the existing app and paired planner. Silver, history, sessions, grind, crafting, OCR and tray controls remain intact. The reader-only native lab remains research and is not installed as the product.

## Use

Open GEAR STUDIO in the Windows app, or select Gear Studio in the planner sidebar. Choose a slot, search the actual Central Market catalog, and select an enhancement. Current equipment and target equipment are separate; empty target slots inherit the current item for the cost comparison. Rings, earrings, artifacts and lightstones have distinct slots. Builds save in browser storage. Export JSON, or use Save Windows backup to save a protected profile copy. Restore adds builds rather than replacing existing ones. The previous Windows backup and normal profile-update backups retain gear files.

Equipment comes from the existing Arsha market API, main categories 1/5/10/15/20/40/45/85. The live NA check returned 1,650 records, including categories that contain life tools and lightstones. Slot filters exclude stationary workshop tools and separate artifact/lightstone types. Only market-listed equipment is available; untradeable items can be absent. The public catalog is cached in the browser separately per region for 24 hours to avoid fetching all categories after every reload. Partial outages retain available/cached categories and are labeled explicitly. Each request has a timeout; there is no gear market poller while idle.

Market details are requested by item ID. Each selected enhancement must fall within exactly one returned minEnhance/maxEnhance interval. A grouped listing is used as returned, not mislabeled as a unique enhancement quote. Unknown/zero/ambiguous prices stay unpriced and totals are marked partial. Regional caches never substitute NA for EU. Caphras levels are notes only, excluded from item valuation and upgrade shopping cost. A Caphras-only change does not count as buying a replacement item.

The upgrade budget is the sum of target market values for changed item IDs/enhancement levels, before selling existing gear. It is not enhancement RNG cost, net profit, tax-adjusted proceeds or a purchase action. Sheet AP/AAP/DP can be entered but are not synthesized from market prices. Verified equipment-stat curves, set effects, class restrictions, journals and crystals need a separate source before an accurate Garmoth-style stat simulation can be offered.

## Three-second tooltip sweep

1. Open the equipment window in BDO. Choose the intended build and current/target side in Gear Studio.
2. Click Import from BDO. There is a three-second lead-in, then a short wait for BDO to become foreground.
3. Move clockwise over equipped items for about three seconds, briefly allowing tooltips to appear. The app captures up to 12 grayscale crops around the pointer, only while BDO is foreground. Repeated stationary hovers retain the last frame so the tooltip can settle.
4. Return to the planner while the captured tooltips are read. Review the item names, enhancement and destination slot, uncheck unwanted candidates, and apply. Unselected slots stay unchanged. Duplicate destination slots and unresolved enhancements block applying the list.

The capture is on demand and stops after the sweep; OCR runs afterward with one worker and a single Tesseract thread. No mouse/keyboard input is sent to the game. Screenshot images are kept in bounded temporary memory and are not written to disk or uploaded. A fast sweep can miss names or tooltip headers. Repeat for remaining pieces, or use a cropped PNG/JPEG tooltip screenshot. Icon-only tiles are not sufficient for reliable identity. Names use exact market matching or conservative fuzzy matching with a margin; every candidate requires review. Roman enhancement is mapped against the item's available level ranges, rather than assuming every V means +20.

The endpoint allows only the paired/local origins, uses one concurrent OCR gate, validates payload/catalog/image size, and returns bounded results. A sweep job exists only when requested; its browser poller stops on completion/error. Native loot OCR code and its configuration are not changed.

## Validation

Eight equipment tests cover real OCR of a generated tooltip image, identity ambiguity, Roman-prefix parsing, duplicate rings, invalid inputs, safe backup retention, same-origin checks and sweep gate recovery. JavaScript core checks cover slot filtering, grouped enhancement quotes, accessory vs weapon Roman levels, bounded imports and partial totals. Full isolated suite: 149 tests passed before the final candidate version bump; rerun results are tracked in the private QA folder. Browser verification selected real Giath's Helmet ID 11013 at enhancement 20 and displayed 2,710,000,000 NA silver from the API. Live user sweep testing is still required before claiming equipment capture accuracy across scales and tooltip layouts.
