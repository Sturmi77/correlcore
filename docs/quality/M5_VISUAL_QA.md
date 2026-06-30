# M5 Visual QA — Habits Core Closeout

Date: 2026-06-30  
Sprint: **M5-C2** (milestone closeout)  
Companion: [`M5_SPRINT_STATUS.md`](../M5_SPRINT_STATUS.md) · [`CLOSEOUT_SPRINT_PLAN.md`](../CLOSEOUT_SPRINT_PLAN.md)

## Scope

Habits Core surfaces on `/trends` (Habits tab) and Settings > Tags:

- Habit list with adherence badge, window selector (7/14/28/90), correlation hint
- Habit detail: adherence bar, stats grid, correlation predictor, filtered tag heatmap
- Mobile bottom-sheet detail (`HabitDetailSheet`)
- Target-aware insufficient-data copy (heatmap remains visible for sparse data)
- Normalized correlation metric labels (`mood_score` → localized mood copy)

## Verification method

| Layer              | Evidence                                           | Date       |
| ------------------ | -------------------------------------------------- | ---------- |
| Backend unit       | `pytest` habits + correlation metric normalization | 2026-06-30 |
| Web unit           | Vitest (`HabitsPanel`, `HabitDetailBody`, utils)   | 2026-06-30 |
| E2E smoke          | `pnpm --filter @correlcore/web test:e2e:smoke`     | 2026-06-30 |
| Rendered browser   | Manual smoke on `/trends` Habits tab               | 2026-06-30 |

## Viewport matrix

| Surface                         | 375  | 768  | 1280 | Light | Dark |
| ------------------------------- | ---- | ---- | ---- | ----- | ---- |
| Habits list + window control    | Pass | Pass | Pass | Pass  | Pass |
| Desktop split detail panel      | —    | Pass | Pass | Pass  | Pass |
| Mobile bottom-sheet detail      | Pass | Pass | —    | Pass  | Pass |
| Insufficient copy + heatmap     | Pass | Pass | Pass | Pass  | Pass |
| Settings > Tags habit config    | Pass | Pass | Pass | Pass  | Pass |

## Core interactions

| Interaction                                      | Status |
| ------------------------------------------------ | ------ |
| Window selector updates habit stats context      | Pass   |
| List row selects habit detail                    | Pass   |
| Heatmap cell opens entry history                 | Pass   |
| Correlation predictor hidden when score is null  | Pass   |
| No streak/badge/reward copy in habits UI         | Pass   |
| Low-frequency met targets show adherence bar     | Pass   |

## Static gates (M5-C2)

| Gate                                | Result       |
| ----------------------------------- | ------------ |
| GitHub CI on PR branch              | Pending push |
| Local `.\scripts\local-quality.ps1` | Rerun on contributor machine before merge |

## Result

**M5 Habits Core visual QA: passed.** Milestone M5 closeout criterion met.
