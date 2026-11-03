# 28 · Simpler layout and navigation

## Audit and decisions

| Surface | Result |
| --- | --- |
| Compact main timer | Keep scan/send/tray controls; clear Home/Craft/Grind shortcuts; secondary tool details remain in More controls |
| Native workspace | Replace the overflowing tab strip with Home/Craft/Grind/Quests plus Planning/History/Readers menus |
| Home | Status and goals first; remove the second row of duplicate navigation |
| Capture setup | Keep crop/feed/interval controls together; keep Track loot visible beside its status |
| Crafting calculator | Highlight the next stage; expand all stages, route comparisons and extra actions only when requested |
| CP Info | Keep quantities and allocation visible; target graphs expand on request |
| Imperial | Retain the four comparison cards and table, with existing advanced details collapsed |
| Grind | Keep session controls, result metrics and progress; fold goal/streaming setup into one expandable group |
| Readers | Keep all loot/tool/quest diagnostics under a named Readers menu |
| History/export | Keep every recorded page and export under History; remove ambiguous global export footer action |

The layout hides secondary controls, not calculations or features. Core OCR,
durability, guild state, recorded item values and sharing choices remain intact.
Menus and disclosures support keyboard focus. Status text accompanies accent
colors; the visible location label identifies the selected page independently.

## Native page contract

`workspace_nav.WorkspaceNavigation` renders the navigation over the original
`ttk.Notebook`. The notebook's tab strip is hidden with its own style, while its
page identities, `select()` API and selection events remain unchanged. This keeps
direct activity links, reader routes and existing tab-specific refresh hooks valid.
All selectable pages have a visible destination in the navigation mapping.

The initial workspace destination is Home. Calling `LootTracker.open()` on an
existing window preserves its selected page. Explicit activity commands still
select their requested page. `open_activity('silver')` is a new internal shortcut
for the compact window's Silver value action; existing names remain supported.

The native CP graph frame does not draw its targets/pie while collapsed. Opening
it draws the current plan, with no additional OCR, data refresh or plan mutation.
The Grind setup disclosure preserves its opt-in controls; it cannot silently
enable OBS or change a saved target merely by expanding.

## Cooking next action

The workshop's next-stage card lists its name, batches, modeled duration, expected
output and stage input quantities. The current confirmation checkbox uses the
same sequential checklist logic as the complete stage list. All stages remain in
an expandable section, together with the route and graph disclosures. IDs and
event handlers for existing controls remain unchanged.

For a multistep plan, both primary timer actions now call the guarded next-stage
launcher. The generic bottom action cannot bypass outstanding intermediate work.
For a one-stage buy-input plan, it still starts that recipe's planning timer.
No checkbox or elapsed timer becomes recorded loot or a game command.

## Refresh efficiency and verification

One visible Grind refresh now calculates its session history once. It reuses that
result for the table, selected summary, median and personal-best comparison. The
loot pulse reuses the summary's existing bins instead of querying and scanning the
same session again. Prices and rate formulas are unchanged. No new polling loop is
introduced by navigation or disclosures.

`test_workspace_navigation.py` verifies every notebook page remains represented,
group names, initial Home, direct activity selection, page preservation and CP
graph expansion without plan changes. Presentation tests assert a single history
calculation per visible refresh. Shipped-page cooking tests verify collapsed
secondary sections, the next card and prevention of intermediate-stage bypass.
Full reader, valuation, privacy, history and packaged checks remain required.
