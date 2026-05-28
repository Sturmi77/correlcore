# M3.6 Sprint Status - Insight Maturity Phases

Last updated: 2026-05-27

Tracking document for [`M3_6_SPRINT_PLAN.md`](M3_6_SPRINT_PLAN.md). M3.6 implements ADR-0021 and `docs/frontend/INSIGHT_MATURITY.md`.

**Milestone completeness:** ✅ Release-complete. Rendered QA passed on 2026-05-27; GitHub issues #188–#192 closed; CI green on `70bb5ed`.

## Overview

| Sprint | Title                                   | Status  | PR / commit (main) | Issues     |
| ------ | --------------------------------------- | ------- | ------------------ | ---------- |
| 0      | API Contract and Shared Types           | ✅ Done | 782e6ba            | #191       |
| 1      | Journey Banner and Explainer            | ✅ Done | 4017c36            | #188       |
| 2      | Insight Cards and Empty States          | ✅ Done | 12bdad4            | #189, #190 |
| 3      | Milestone Notifications and Preferences | ✅ Done | 12bdad4            | #192       |
| 4      | Visual QA, Docs and GitHub Closure      | ✅ Done | closeout docs      | #188-#192  |

## GitHub Issue Closure

| Issue | Status | Closed     |
| ----- | ------ | ---------- |
| #188  | Closed | 2026-05-26 |
| #189  | Closed | 2026-05-26 |
| #190  | Closed | 2026-05-26 |
| #191  | Closed | 2026-05-26 |
| #192  | Closed | 2026-05-26 |

## Sprint 0 - API Contract and Shared Types

- [x] Backend maturity phase calculation from distinct tracked entry days
- [x] `insight_maturity` object on `/api/v1/insights` and `/api/v1/insights/latest`
- [x] API docs updated in `docs/API.md`
- [x] Frontend API type and insight store contract updated
- [x] Phase boundary tests for 1, 6, 7, 13, 14, 29, 30+
- [x] CI-confirmed backend/web gates on `70bb5ed`

## Sprint 1 - Journey Banner and Explainer

- [x] `InsightJourneyBanner`
- [x] `InsightJourneyExplainer`
- [x] Insights page placement
- [x] Home collapsible variant
- [x] DE/EN `maturity.*` copy
- [x] Component tests for render, explainer open and collapsed variant
- [x] CI-confirmed web gates on `70bb5ed`

## Sprint 2 - Insight Cards and Empty States

- [x] `InsightMaturityBadge`
- [x] Insight card confidence display replacement in default card state
- [x] Statistical confidence details kept in expanded/detail state
- [x] Phase-aware empty/locked-state messaging for Insights feed
- [x] Uncertainty hints for `early_patterns` and `provisional`
- [x] Component tests for badge rendering and phase-aware empty states
- [x] CI-confirmed web gates on `70bb5ed`

## Sprint 3 - Milestone Notifications and Preferences

- [x] One-time phase milestone card
- [x] Preference persistence for dismissed phase milestones via `reached_milestone_keys`
- [x] Explicit-dismiss behavior, not toast/auto-dismiss
- [x] Reduced-motion handling
- [x] Component and helper tests for milestone visibility/dismiss
- [x] CI-confirmed web gates on `70bb5ed`

## Sprint 4 - Closeout

- [x] Repo aligned with `origin/main` at `70bb5ed`
- [x] GitHub `CI — Web` green on current `main`
- [x] GitHub issues #188–#192 closed
- [x] Rendered QA for all phases — see [`docs/quality/M3_6_VISUAL_QA.md`](quality/M3_6_VISUAL_QA.md)
- [x] Mobile/desktop and light/dark verification passed
- [x] Sprint status and design-doc checklists updated

## Next Up

M3.7 — Color System Hardening (see [`docs/M3_7_SPRINT_PLAN.md`](M3_7_SPRINT_PLAN.md)). M4 — Mobile/PWA hardening follows after M3.7.
