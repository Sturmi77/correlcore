# M3.6 Sprint Status - Insight Maturity Phases

Last updated: 2026-05-16

Tracking document for [`M3_6_SPRINT_PLAN.md`](M3_6_SPRINT_PLAN.md). M3.6 implements ADR-0021 and `docs/frontend/INSIGHT_MATURITY.md`.

## Overview

| Sprint | Title                                   | Status | PR / commit (main) | Issues     |
| ------ | --------------------------------------- | ------ | ------------------ | ---------- |
| 0      | API Contract and Shared Types           | Open   | -                  | #191       |
| 1      | Journey Banner and Explainer            | Open   | -                  | #188       |
| 2      | Insight Cards and Empty States          | Open   | -                  | #189, #190 |
| 3      | Milestone Notifications and Preferences | Open   | -                  | #192       |
| 4      | Visual QA, Docs and GitHub Closure      | Open   | -                  | #188-#192  |

## GitHub Milestone Assignment

Target GitHub milestone: **M3.6 — Insight Maturity Phases**.

| Issue | Current repo state checked via public API | Target milestone               |
| ----- | ----------------------------------------- | ------------------------------ |
| #188  | Open, no milestone                        | M3.6 — Insight Maturity Phases |
| #189  | Open, no milestone                        | M3.6 — Insight Maturity Phases |
| #190  | Open, no milestone                        | M3.6 — Insight Maturity Phases |
| #191  | Open, no milestone                        | M3.6 — Insight Maturity Phases |
| #192  | Open, no milestone                        | M3.6 — Insight Maturity Phases |

Tooling blocker: this agent environment has no `gh` executable and no `GH_TOKEN` / `GITHUB_TOKEN`. Milestone creation and issue assignment must therefore be completed manually or from an authenticated shell.

## Sprint 0 - API Contract and Shared Types

- Backend maturity phase calculation
- `insight_maturity` object on all insight endpoints
- OpenAPI / API docs
- Frontend API type
- Phase boundary tests

## Sprint 1 - Journey Banner and Explainer

- `InsightJourneyBanner`
- `InsightJourneyExplainer`
- Insights page placement
- Home collapsible variant
- DE/EN copy

## Sprint 2 - Insight Cards and Empty States

- `InsightMaturityBadge`
- Insight card confidence display replacement
- Phase-aware empty states
- Phase-aware locked states
- Uncertainty hints for early/provisional content

## Sprint 3 - Milestone Notifications and Preferences

- One-time phase milestone card
- Preference persistence for dismissed phase milestones
- Explicit-dismiss behavior
- Reduced-motion handling

## Sprint 4 - Closeout

- Rendered QA for all phases
- Mobile/desktop and light/dark verification
- i18n completeness
- No-gamification copy review
- GitHub issue closure / rescope

## Next Up

Create or select the GitHub milestone **M3.6 — Insight Maturity Phases**, assign #188-#192, then start Sprint 0 with the API contract extension (#191).
