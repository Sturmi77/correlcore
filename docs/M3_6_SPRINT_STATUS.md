# M3.6 Sprint Status - Insight Maturity Phases

Last updated: 2026-05-16

Tracking document for [`M3_6_SPRINT_PLAN.md`](M3_6_SPRINT_PLAN.md). M3.6 implements ADR-0021 and `docs/frontend/INSIGHT_MATURITY.md`.

## Overview

| Sprint | Title                                   | Status                  | PR / commit (main) | Issues     |
| ------ | --------------------------------------- | ----------------------- | ------------------ | ---------- |
| 0      | API Contract and Shared Types           | Implemented, CI pending | pending CI         | #191       |
| 1      | Journey Banner and Explainer            | Implemented, CI pending | local changes      | #188       |
| 2      | Insight Cards and Empty States          | Implemented, CI pending | local changes      | #189, #190 |
| 3      | Milestone Notifications and Preferences | Implemented, CI pending | local changes      | #192       |
| 4      | Visual QA, Docs and GitHub Closure      | Open                    | -                  | #188-#192  |

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

- [x] Backend maturity phase calculation from distinct tracked entry days
- [x] `insight_maturity` object on `/api/v1/insights` and `/api/v1/insights/latest`
- [x] API docs updated in `docs/API.md`
- [x] Frontend API type and insight store contract updated
- [x] Phase boundary tests for 1, 6, 7, 13, 14, 29, 30+
- [ ] CI-confirmed backend/web gates after commit

## Sprint 1 - Journey Banner and Explainer

- [x] `InsightJourneyBanner`
- [x] `InsightJourneyExplainer`
- [x] Insights page placement
- [x] Home collapsible variant
- [x] DE/EN `maturity.*` copy
- [x] Component tests for render, explainer open and collapsed variant
- [ ] CI-confirmed web gates after commit

## Sprint 2 - Insight Cards and Empty States

- [x] `InsightMaturityBadge`
- [x] Insight card confidence display replacement in default card state
- [x] Statistical confidence details kept in expanded/detail state
- [x] Phase-aware empty/locked-state messaging for Insights feed
- [x] Uncertainty hints for `early_patterns` and `provisional`
- [x] Component tests for badge rendering and phase-aware empty states
- [ ] CI-confirmed web gates after commit

## Sprint 3 - Milestone Notifications and Preferences

- [x] One-time phase milestone card
- [x] Preference persistence for dismissed phase milestones via `reached_milestone_keys`
- [x] Explicit-dismiss behavior, not toast/auto-dismiss
- [x] Reduced-motion handling
- [x] Component and helper tests for milestone visibility/dismiss
- [ ] CI-confirmed web gates after commit

## Sprint 4 - Closeout

- Rendered QA for all phases
- Mobile/desktop and light/dark verification
- i18n completeness
- No-gamification copy review
- GitHub issue closure / rescope

## Next Up

Run/confirm the Sprint 3 web gates, then continue with Sprint 4 closeout QA. GitHub milestone assignment for #188-#192 remains blocked in this agent environment by missing `gh`/token tooling.
