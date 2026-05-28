# M3.5 Visual QA Closeout

Date: 2026-05-27

Scope: M3.5 frontend and mobile optimisation across Home, Entry Sheet, Insights, Trends, Settings, and Tag Settings.

## Result

**M3.5 release closeout: passed.**

Rendered browser QA was executed from the local clone `C:\Users\micha\correlcore-ci` against `main` at `70bb5ed` via `pnpm.cmd dev` on `http://localhost:5173/`. Login, core navigation, and the M3.5 interaction matrix completed without blocking defects.

## Completeness Snapshot

| Area                       | Status   | Notes                                                                                         |
| -------------------------- | -------- | --------------------------------------------------------------------------------------------- |
| Sprint implementation      | Complete | Sprints 0–9 on `main`.                                                                        |
| Static documentation       | Complete | `FRONTEND.md`, `M3_5_SPRINT_STATUS.md`, `CHANGELOG.md`, this handoff.                         |
| Rendered viewport/theme QA | Complete | 375 / 768 / 1280 px, light and dark — no horizontal scroll or touch-target blockers observed. |
| GitHub issue closure       | Complete | #170–#185 closed or rescoped; #186 closed after this QA pass.                                 |
| CI verification            | Complete | `CI — Web` green on `70bb5ed`; Playwright smoke and unit gates pass in CI.                    |
| Release image verification | Complete | `Release — Container Images` succeeds on current `main`.                                      |

## Viewport Matrix

| Viewport   | Intended Coverage                                                               | Status |
| ---------- | ------------------------------------------------------------------------------- | ------ |
| 375 x 812  | Mobile bottom nav, Entry Sheet, stacked settings/tag rows, no horizontal scroll | Pass   |
| 768 x 1024 | Tablet side nav breakpoint and sheet/modal transitions                          | Pass   |
| 1280 x 800 | Desktop layout, trends charts, settings sections, insight feed density          | Pass   |

## Theme Matrix

| Theme | Intended Coverage                                        | Status |
| ----- | -------------------------------------------------------- | ------ |
| Light | Surface/card contrast, focus rings, chart/heatmap colors | Pass   |
| Dark  | Surface/card contrast, focus rings, chart/heatmap colors | Pass   |

## Core Interactions

| Interaction                                                 | Rendered QA |
| ----------------------------------------------------------- | ----------- |
| Home -> Entry Sheet -> Auto-Save -> Day Delta               | Pass        |
| Insights -> Filter -> Disclaimer -> Details                 | Pass        |
| Trends -> Tab -> Data point -> Entry History Sheet          | Pass        |
| Settings -> Language -> Theme -> Dev Unlock -> Force Viz    | Pass        |
| Tag Settings -> deactivate/reactivate -> picker hidden tags | Pass        |

## Evidence

- Local environment: Windows, Chrome, `pnpm.cmd dev`, clone `C:\Users\micha\correlcore-ci`.
- Automated regression: GitHub `CI — Web` on `70bb5ed` (lint, typecheck, unit tests, build, Playwright smoke).
- No-gamification copy remains covered by `apps/web/src/lib/i18n/noGamificationCopy.test.ts`.
