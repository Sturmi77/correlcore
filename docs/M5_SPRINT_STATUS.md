# M5 Sprint Status - Habits Core ohne Gamification

Last updated: 2026-06-30

Tracking document for [`docs/M5_SPRINT_PLAN.md`](M5_SPRINT_PLAN.md).

**Milestone completeness:** Habits Core complete on `main` after M5-C1 (#241) and M5-C2 closeout.
Visual QA signed off in [`docs/quality/M5_VISUAL_QA.md`](quality/M5_VISUAL_QA.md).

## Overview

| Sprint | Title                   | Status |
| ------ | ----------------------- | ------ |
| 0      | Scope & Docs            | Done   |
| 1      | Backend Habit Contracts | Done   |
| 2      | Habit Configuration UI  | Done   |
| 3      | Trends Habits Tab       | Done   |
| 4      | No-Gamification Polish  | Done   |
| 5      | Closeout                | Done   |

## Completed

- [x] M5 scope fixed to Habits Core; co-occurrence moved to M5.1/backlog.
- [x] `TagCreate`, `TagUpdate` and `TagResponse` expose habit fields.
- [x] `GET /api/v1/habits` and `GET /api/v1/habits/{tag_id}/stats` added.
- [x] Settings > Tags can configure `none | build | reduce` and weekly target.
- [x] `/trends` includes a Habits tab with list, window control and detail.
- [x] Habit detail reuses the M2 tag heatmap filtered to the selected habit.
- [x] EN/DE copy avoids streak, reward, badge and urgency framing.
- [x] Habit list shows adherence badge with window context and correlation summary (#157/#159).
- [x] Habit detail shows adherence progress bar, heatmap, and correlation predictor copy (#159).
- [x] Mobile bottom-sheet detail via `HabitDetailSheet` (#159).
- [x] Target-aware insufficient-data state; heatmap stays visible for sparse habits (#159).
- [x] `correlation_metric` normalized for display (`mood_score` → mood label).
- [x] Rendered QA at 375/768/1280 in light and dark — [`M5_VISUAL_QA.md`](quality/M5_VISUAL_QA.md).
- [x] GitHub issues #157/#159 closed; milestone #6 closed.
