# M3.6 Sprint Plan - Insight Maturity Phases

Last updated: 2026-05-16

M3.6 introduces the ADR-0021 insight maturity phase model as an implementation milestone between M3.5 and M4.

## Goal

Implement insight maturity as a first-class product and API concept. The frontend must no longer treat insights as a binary "locked/unlocked at 30 entries" feature. Instead, Home, Insights, and related empty/locked states use the shared four-phase model from ADR-0021:

| Phase | Key | Entry Range | UI Label | Scope |
| --- | --- | --- | --- | --- |
| 1 | `collecting` | 1-6 | Collecting Data | Foundation, entry history, simple data completeness |
| 2 | `early_patterns` | 7-13 | First Patterns | Trends, frequency charts, first descriptive patterns |
| 3 | `provisional` | 14-29 | Provisional Insights | Emerging relationships with explicit uncertainty |
| 4 | `robust` | 30+ | Robust Insights | Full insight engine, stronger statements, recommendations |

## Sources of Truth

- [ADR-0021](adr/0021-insight-maturity-phases.md)
- [Insight Maturity frontend specification](frontend/INSIGHT_MATURITY.md)
- `docs/DESIGN_DOCUMENT.md` - roadmap and product philosophy
- `docs/FRONTEND.md` - implemented screen rules

## GitHub Issues

These issues should be assigned to the GitHub milestone **M3.6 — Insight Maturity Phases**.

| Issue | Title | Area | Status |
| --- | --- | --- | --- |
| #188 | Insight Maturity: InsightJourneyBanner component | Frontend | Open |
| #189 | Insight Maturity: InsightMaturityBadge replaces raw confidence score | Frontend | Open |
| #190 | Insight Maturity: phase-aware empty & locked states on Insights page | Frontend / UX | Open |
| #191 | Insight Maturity: API contract extension (`insight_maturity` object) | Backend / API | Open |
| #192 | Insight Maturity: phase milestone notification card | Frontend / UX / Preferences | Open |

Tooling note: this agent environment currently has no `gh` executable and no `GH_TOKEN` / `GITHUB_TOKEN`, so GitHub milestone creation and issue assignment must be completed manually or from an authenticated environment.

## Sprint Breakdown

### Sprint 0 - API Contract and Shared Types

- Add backend maturity calculation from tracked entry count.
- Extend all `/api/v1/insights/*` responses with `insight_maturity`.
- Add OpenAPI / `docs/API.md` documentation.
- Add frontend API types for `InsightMaturity`.
- Tests for all phase boundaries: 1, 6, 7, 13, 14, 29, 30+.

### Sprint 1 - Journey Banner and Explainer

- Implement `InsightJourneyBanner`.
- Add `InsightJourneyExplainer` as bottom sheet / modal.
- Place banner on Insights; add collapsible variant for Home.
- Add DE/EN `maturity.*` copy.
- Ensure no frontend recomputation of phase; read only from API.

### Sprint 2 - Insight Cards and Empty States

- Replace raw card confidence presentation with `InsightMaturityBadge`.
- Keep statistical details only in expanded/detail contexts where appropriate.
- Refactor Insights empty and locked states to explain the current phase.
- Add uncertainty hints for `early_patterns` and `provisional`.

### Sprint 3 - Milestone Notifications and Preferences

- Add one-time phase milestone card for phase transitions.
- Persist dismissed phase milestones in user preferences.
- Ensure cards are explicit-dismiss only and not toasts.
- Add reduced-motion handling for any robust-phase completion animation.

### Sprint 4 - QA and Closeout

- Rendered QA across Home and Insights for all four phases.
- Mobile and desktop viewport checks.
- Light/dark checks.
- i18n completeness check.
- No-gamification review of phase/milestone copy.
- Assign/close GitHub issues #188-#192.

## Acceptance Criteria

- API returns `insight_maturity` for all insight endpoints.
- Frontend never computes maturity phase independently from entry count.
- `InsightJourneyBanner` renders correctly for all four phases.
- `InsightMaturityBadge` appears on every eligible insight card.
- Empty and locked states are phase-aware.
- Phase milestone card appears once per transition and persists dismiss state.
- All `maturity.*` i18n keys exist in DE and EN.
- No raw p-values or numeric confidence scores appear in default user-facing card states.
- Copy remains non-medical, non-causal, and non-gamified.

## Exit Criteria

- Issues #188-#192 are assigned to the M3.6 milestone and closed or deliberately rescoped.
- Backend, web typecheck/lint/test/build gates pass in CI.
- Rendered browser QA confirms all phases in light/dark and mobile/desktop.
- `docs/M3_6_SPRINT_STATUS.md`, `CHANGELOG.md`, `docs/API.md`, and `docs/FRONTEND.md` reflect the implementation.
