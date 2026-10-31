# Equipment import correction — 2026-10-30

The first live feedback supplied two identical copies of one 2,965-line OCR diagnostic. They count as one input, not two independent accuracy samples. The text contained readable `PEN: Kharazad Belt` and `Distorted Labreskats Helmet`, while other tooltip names were clipped or fragmented. The broad scene output also contained descriptions mentioning equipment; those mentions are not evidence that an item is equipped.

## Corrections

- Parse a bounded 64 KB / 4,000 nonempty lines rather than only the first 150 raw lines. This avoids spending the input allowance on blanks and sparse scene noise.
- Accept `PEN:`, rank-plus-Roman notation and a standalone rank preceding an item-name line. Conflicting rank/Roman pairs remain unresolved.
- Recognize Desperate/Distorted/Silent/Wailing/Obliterating only for Labreska's Helmet, Fallen God's Armor, Dahn's Gloves and Ator's Shoes. A Distorted title maps to numeric level 2; it is not guessed from DP or price.
- Index fuzzy candidates by the final equipment noun, retaining a strict score and separation margin. Reject description, enhancement-instruction and Cron Stone mentions. Never reconstruct a missing title from flavor text.
- Preserve complete tooltip-area bounds near the edge of the game window. At normal 1080p height the vertical crop covers the whole game height, preventing a lower-slot hover from cutting off a tall tooltip's header. Maximum temporary frame buffers: twelve 1280×1440 grayscale images, about 22 MiB; no permanent capture loop or image files.
- Request coordinates from the existing sparse OCR pass. If identity or enhancement is uncertain, retry at most two small equipment-header regions in text-block mode, with dark-header inversion where appropriate. Focused text is shown before scene noise in diagnostics.
- Read four Kharazad identities from the existing local index only when the name has one exact ID. Keep them marked untradeable, editable through level 10 and unpriced. No inferred market value is assigned. Named Slumbering Origin level ranges also remain editable when quotes are unavailable; no price is fabricated.

## Evidence

The old parser plus market-only fixture recovered zero candidates from the supplied diagnostic. The updated parser plus verified local supplement recovers Kharazad Belt, PEN (V), and Labreska's Helmet, Distorted / DUO (II). The audit uses a small equipment identity fixture and the real local Kharazad index; it is a targeted regression, not a full catalog or live pixel-accuracy benchmark. Description-only Dahn/Fallen God references are withheld. Their missing/clipped titles still need a clearer next capture.

156 isolated full-app tests pass. The 15 gear tests include actual OCR of a generated tooltip, parser noise/rank regressions, unique identity enforcement, screen-edge geometry, focused-header retry behavior, duplicate accessories, backups and origin/concurrency checks. JavaScript checks cover grouped prices, preserved unknown stats, untradeable metadata and excluded/unpriced upgrade amounts. New capture geometry still requires another live sweep across the user's equipment layout; the supplied text alone cannot prove pixel-level improvement.

Private diagnostic files and reports stay outside the repository under the workspace's `qa-22/`. No player chat, character identifiers, screenshots or history databases are published.

References: [Pearl Abyss Kharazad update and enhancement progression](https://blackdesert.pearlabyss.com/Asia/en-US/News/Notice/Detail?_boardNo=6504), [Pearl Abyss Slumbering Origin glove rank names](https://blackdesert.pearlabyss.com/Asia/en-US/News/Notice/Detail?_boardNo=3855), [Labreska rank table](https://garmoth.com/guides/post/labreskas-helmet/). The local catalog supplies item identity; these references do not supply live market prices.
