# M7 / M8 Milestone Swap

Last updated: 2026-05-29

This document records the deliberate reordering of milestones **M7** and **M8**
effective 2026-05-29. It is the canonical reference when older issues, chat
logs, or commits still mention the pre-swap numbering.

## Summary

| Milestone | Before 2026-05-29       | After 2026-05-29                                                                        |
| --------- | ----------------------- | --------------------------------------------------------------------------------------- |
| **M7**    | Schlaf & Health Connect | **Insights v2** (Lasso, lag, symptom analytics, clustering, optional Ollama)            |
| **M8**    | Insights v2             | **Schlaf & Health Connect** (manual sleep fields, wearable import, sleep↔mood insights) |

Roadmap order is now: … M5 → **M7 Insights v2** → **M8 Sleep/HC** → M9 … → M13 Photos.

## Rationale

1. **Platform fit:** Insights v2 is backend + web worker work and extends the
   existing M3 analytics pipeline. It does not require Android or Health Connect.
2. **Data readiness:** Lasso, lag analysis, and symptom analytics run on
   entries, tags, symptoms, and `cycle_day` — all already shipped (M1–M5, M4).
3. **Health Connect timing:** Full Health Connect import depends on the Capacitor
   Android path (M11). Delivering Insights v2 first avoids blocking web/selfhost
   users on mobile-native work.
4. **Clean extension:** When M8 lands, sleep metrics become additional columns in
   the M7 design matrix — no rewrite of the insight engine.

## Technical consequences

| Area                 | Impact                                                                                                                                  |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend / worker** | No code change required for the swap. M3 `insight_engine.py` remains the base; M7 extends it.                                           |
| **Database**         | No migration required until each milestone is implemented. Sleep columns remain a future M8 migration.                                  |
| **API**              | `GET /api/v1/insights/*` contract unchanged. New insight types ship under M7. Sleep fields on entries ship under M8.                    |
| **Frontend**         | M7: `/insights` feed extensions, symptom visualisations, optional clustering UI. M8: entry sleep fields, HC consent screens (with M11). |
| **Export**           | `photos: []` and `sleep: []` stay empty until M13 / M8 respectively.                                                                    |
| **MinIO / infra**    | Unchanged.                                                                                                                              |

## Product consequences

| Topic                | M7 first (Insights v2)                          | M8 later (Sleep/HC)                                                   |
| -------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| Web/selfhost users   | Richer correlations without wearables           | Manual sleep entry first; auto-import when Android ships              |
| Wearable-first users | Wait for sleep auto-import                      | Unchanged ultimate delivery, better insight surface when data arrives |
| M10 v1.0 selfhost    | Can ship with Insights v2, without sleep import | Acceptable: sleep is SHOULD, not MUST for v1.0                        |
| M11 Play Store       | HC declaration still tied to M8 + M11           | No change                                                             |

## Deferred / split work (unchanged intent, new labels)

| Work item                                                             | New milestone                                      |
| --------------------------------------------------------------------- | -------------------------------------------------- |
| Lasso (#144), lag (#145), symptom analytics epic, pgvector clustering | **M7**                                             |
| Sleep×Symptom association (when sleep metrics exist)                  | **M8** (side effect of sleep integration)          |
| Cycle × lifestyle correlations (uses `cycle_day`)                     | **M7**                                             |
| Health Connect cycle import & phase bands                             | **M8** (see [`M8_NOTES.md`](M8_NOTES.md))          |
| M5.1 tag co-occurrence heatmap                                        | M5.1/backlog — optional precursor to M7 clustering |
| Issue #172 sleep_quality UI field                                     | **M8** (was already deferred from M3.5)            |

## Documentation index (post-swap)

| Document                                                                           | Role                                                         |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md)                                         | M7/M8 milestone sections and acceptance criteria             |
| [`M7_NOTES.md`](M7_NOTES.md)                                                       | Insights v2 implementation notes (clustering, prerequisites) |
| [`M8_NOTES.md`](M8_NOTES.md)                                                       | Sleep, Health Connect, cycle deep integration                |
| [`features/symptom-analytics.md`](features/symptom-analytics.md)                   | Symptom analytics milestone mapping                          |
| [`adr/0016-timeseries-split-ml-models.md`](adr/0016-timeseries-split-ml-models.md) | TimeSeriesSplit — milestone M7                               |
| [`adr/0025-symptom-analytics.md`](adr/0025-symptom-analytics.md)                   | Rollout order M7 → M8 for symptom levels                     |
| [`features/notes-in-analysis.md`](features/notes-in-analysis.md)                   | Signal extraction tied to M7 Insights v2                     |
| [`adr/0003-sync-conflict-log.md`](adr/0003-sync-conflict-log.md)                   | CRDT future path uses chronological M9 (not feature M8)      |

## GitHub issues and historical text

Issues created before 2026-05-29 may still say "M7" for sleep or "M8" for
Lasso. When triaging, map using the table above. Do not renumber closed issues;
add a comment with the new milestone label if still open.
