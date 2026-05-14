# M3 Sprint Status — Insights v1

Last updated: 2026-05-14  
Status: **✅ Complete**

This document records the closed state of M3 (Insights v1). For the
post-M3 polish iteration see [M3.1_SPRINT_STATUS.md](./M3.1_SPRINT_STATUS.md).

## Sprint Overview

| Sprint | Status    | Summary                                                                                    |
| ------ | --------- | ------------------------------------------------------------------------------------------ |
| 1      | ✅ Closed | No-gamification prep: entry run copy updated to Tracking Consistency.                      |
| 2      | ✅ Closed | Insight & Preference foundation: migration, models, schemas, analytics dependencies.       |
| 3      | ✅ Closed | Analytics Engine v1: tiered candidates, Spearman, Point-biserial, Weekday Pattern.         |
| 4      | ✅ Closed | Analytics Worker: nightly insight generation for active / verified users.                  |
| 5      | ✅ Closed | Read API: `GET /api/v1/insights` and `/insights/latest`.                                   |
| 6      | ✅ Closed | Web Home Preview: latest insight rendered read-only on the Home screen.                    |
| 7      | ✅ Closed | Statistics hardening: FDR correction, minimum sample size, weekday bias, entry-date guard. |
| 8      | ✅ Closed | Insight Confidence Scale: dashboard summary endpoint and persistent Home scale.            |
| 9      | ✅ Closed | First-Week UX: WeekdayPatternChart, neutral banner, preference dismiss state.              |
| 10     | ✅ Closed | Insights page and correlation matrix for tag–mood patterns.                                |
| 11     | ✅ Closed | Cold-start onboarding: retro batch, profile questionnaire, static preview library.         |
| 12     | ✅ Closed | Day-over-Day Delta: direct comparison to yesterday after entry save.                       |

## Implementation Summary

- **#151 Tiered Confidence System:** `Insight` model/API/worker deliver `tier`, `confidence`, and `sample_n`. Home renders tier badge, explanatory tooltip/ARIA text, visible medical disclaimer, and neutral copy without causal or diagnostic claims.
- **#152 Retrospective Entry Import:** `EntrySource`, migration, `POST /api/v1/entries/batch`, `/onboarding/retro`, and persisted `onboarding_retro_completed` state are implemented.
- **#153 Insight Confidence Scale:** `GET /api/v1/dashboard/summary`, logarithmic `confidence_score`, and `InsightConfidenceScale` on Home are implemented.
- **#154 Day-over-Day Delta:** `GET /api/v1/entries/delta?entry_date=YYYY-MM-DD&slot=day`, metric-only response, shared tags, and `DayDeltaCard` on `/entries/new` after auto-save or when loading existing entries are implemented.
- **#155 First-Week Tracking Consistency Insight:** weekday payload, 7-bar chart, neutral banner, and persistent `dismissed_insight_keys` state are implemented.
- **#156 Onboarding Questionnaire:** `user_profiles`, `PUT /api/v1/user/profile`, export extension, `/onboarding/profile`, and `insight_previews.json` with clearly labelled general research notes are implemented.
- **#157 and #159:** intentionally deferred outside M3 as M5 follow-up work.
- **#158:** M2 follow-up is implemented and closed in GitHub.

## Final Verification Gate

All checks passed on branch `m3-completion-plan` before merge to `main`:

```
uv run --python 3.12 ruff check .                   ✅
uv run --python 3.12 ruff format --check .          ✅
uv run --python 3.12 mypy app                       ✅
pytest --no-cov                     372 tests ✅
pnpm --filter @correlcore/web typecheck             ✅
pnpm --filter @correlcore/web lint                  ✅
pnpm --filter @correlcore/web test -- --run  195 tests ✅
pnpm --filter @correlcore/web build                 ✅
```

> The valid test Fernet key is set only for local test runs.
> The local `.env` retains the documented placeholder key.

## Post-M3 Work

See [M3.1_SPRINT_STATUS.md](./M3.1_SPRINT_STATUS.md) for the follow-up polish
iteration covering InsightCard, InsightStore non-blocking load, CorrelationDisclaimer,
and heatmap neutralisation.
