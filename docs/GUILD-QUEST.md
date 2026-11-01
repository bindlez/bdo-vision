# Alchemy Guild Quest

Open **GUILD QUEST** from the native home window or its activity tabs. Enable **Track alchemy guild quest** and return to BDO with the current alchemy guild objective visible in the right-hand quest widget. The default crop follows the game client window; no initial rectangle is needed for the standard layout. Use **CUSTOM AREA** if the widget was moved or the display is unusually large. Include the guild heading and its current objective; avoid the mission browser/list.

The tracker shows verified current/target, percent, units remaining and the age of the last reading. Recent observed pace appears after enough increasing samples. The default near-finish warning is 95%, editable to 80/85/90/95/99%. It beeps and keeps a visible message once near the threshold and once at completion. **TEST ALERT** changes no counts. **READ NOW** gives three seconds to return to BDO.

Progress and delivered-alert flags persist in the protected profile database. **NEXT QUEST** archives the previous snapshot and rearms alerts. After a completed objective, a reset/lower counter needs two separate readings before it is treated as a new quest. An unexpected decrease or different goal during an unfinished quest stays uncertain.

## Measurement boundaries

This reads one displayed alchemy guild objective, not every mission or the guild's unrendered state. It does not add local loot to a shared-guild total. Both OCR polarities must agree. Personal quest counters outside the guild objective are excluded. Hidden, covered, stale or unclear text keeps last verified progress and pauses measurement. No alerts are inferred while the game is in its tray or the objective is absent. Complete means the tracked objective reached its target; check BDO for any remaining mission conditions and accept the next quest yourself.

English text is supported in this candidate. Input is limited to 250,000 pixels and prepared OCR to 1.5 million pixels. Automatic scans occur about every ten seconds, after existing reader work; blocked checks back off. A single verified exact-frame result can be reused briefly, with no full-image cache. Screenshot logging is not enabled. When this feature is off, it starts no worker and schedules no guild polling. The visible tab reuses the app's existing UI clock.

The small read-only local `/guild-quest` diagnostic route uses the existing Host/origin restrictions and returns only objective/status summaries. No new website polling or backend is added.

Validation: the saved real widget read **Mysterious Catalyst 184/600** in both passes and excluded the nearby **2/100** personal quest. Generated-widget real OCR, disagreement rejection, threshold alerts, restart behavior, stale/blocked capture, counter regressions and archived/new-quest transitions are tested. Live completion of a real guild mission is not claimed.

rc.5 also verifies the real **593/600** near-finish frame. A small focused gold-heading fallback recovers guild context lost by whole-widget OCR; two objective counts still must agree. A replay of 184 → 593 → 593 triggers one near alert, then no repeat. Work is bounded to three seconds per guild read, and unclear objectives back off rather than repeatedly launching OCR.
