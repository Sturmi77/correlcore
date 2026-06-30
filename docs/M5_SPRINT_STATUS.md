# M5 Sprint Status - Habits Core ohne Gamification

Last updated: 2026-06-30

Tracking document for [`docs/M5_SPRINT_PLAN.md`](M5_SPRINT_PLAN.md).

**Milestone completeness:** Habits Core merged on `main` (PR #212). Closeout
(rendered QA, full gate rerun, issue closure) is still in verification.

## Overview

| Sprint | Title                   | Status          |
| ------ | ----------------------- | --------------- |
| 0      | Scope & Docs            | Done            |
| 1      | Backend Habit Contracts | Done            |
| 2      | Habit Configuration UI  | Done            |
| 3      | Trends Habits Tab       | Done            |
| 4      | No-Gamification Polish  | Done            |
| 5      | Closeout                | Pending         |

## Completed

- [x] M5 scope fixed to Habits Core; co-occurrence moved to M5.1/backlog.
- [x] `TagCreate`, `TagUpdate` and `TagResponse` expose habit fields.
- [x] `GET /api/v1/habits` and `GET /api/v1/habits/{tag_id}/stats` added.
- [x] Settings > Tags can configure `none | build | reduce` and weekly target.
- [x] `/trends` includes a Habits tab with list, window control and detail.
- [x] Habit detail reuses the M2 tag heatmap filtered to the selected habit.
- [x] EN/DE copy avoids streak, reward, badge and urgency framing.
- [x] Habit list shows adherence badge with window context and correlation summary (#159).
- [x] Habit detail shows adherence progress bar, heatmap, and correlation predictor copy (#159).
- [x] Mobile bottom-sheet detail via `HabitDetailSheet` (#159).
- [x] Insufficient-data empty state when fewer than 7 tracked days (#159).
- [x] `correlation_metric` exposed on habit stats API for mood/metric labeling.

## Remaining Closeout

- [ ] Full backend gates: `ruff`, `mypy`, `pytest --cov`.
- [ ] Full web gates: `svelte-check`, ESLint, Vitest, `pnpm check:contrast`.
- [ ] Rendered QA at 375/768/1280 in light and dark.
- [ ] GitHub issues #157/#159 closed or commented after closeout.
