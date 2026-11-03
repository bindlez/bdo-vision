# App feature audit · 2026-11-03

Public reference: [Garmoth app](https://garmoth.com/app). This compares the app
feature section, not every tool linked in its site navigation. Public claims
aren't independently tested behavior. Vision statuses describe implemented scope.

| Feature | Vision status |
| --- | --- |
| Loot and session valuation | Implemented; capture gaps and unpriced items explicit |
| Desktop widgets | Partial: compact live window, not freely arranged widgets |
| OBS | Implemented locally; independent opt-in, clock/loot visibility flags |
| Item and silver targets | Implemented |
| Automated session lifecycle | Gap: manual controls remain |
| Combat/life classification | Gap: no verified automatic classification |
| Language coverage | Gap: English production reader |
| Market regions | Gap: NA/EU integration |
| Community buff reporting | Gap: no reporting service |
| Cloud profile/submission | Gap: local profiles and exports only |
| Automatic updates | Gap: checked downloadable releases, manual installation |
| Font/scale reliability | Partial: bounded reader variants; broad live acceptance pending |

## Integration priorities, not parity claims

1. Preserve accepted-event accuracy and visible diagnostics. Additional automation
   must never infer loot merely because a timer ran or the game was obscured.
2. Add separately opted-in lifecycle automation with restart/manual-pause tests.
   Pause and end thresholds need to distinguish unreadable capture from no drops.
3. Add localized item catalogs and frozen regression sets before enabling another
   language. A translated dropdown does not constitute OCR language support.
4. Add market-provider region coverage only after verifying exact item identities,
   stale/offline behavior and regional prices. Do not reuse NA quotes elsewhere.
5. Cloud profiles, community reports and signed updates need their own service,
   privacy choices, authentication and recovery work. No silent upload endpoints.

## Vision additions in this candidate

The teal accent accompanies explicit statuses; color never carries meaning alone.
Grind adds value-composition and time-coverage donuts. Personal-best pacing compares
the same spot/activity against completed runs of at least ten observed minutes,
revalued using the current price book. Missing item prices withhold the comparison.
It uses captured value, not estimated missed drops or a claim about future RNG.

The live window is opened explicitly and uses the existing app tick. OBS sharing
is off by default and independent of planner sharing. The stream endpoint exposes
only its small current-run snapshot. Turning sharing off rejects requests; stale
or offline browser views clear rather than presenting old totals as live.

Full competitor parity is not complete. These gaps remain in the active task list.
