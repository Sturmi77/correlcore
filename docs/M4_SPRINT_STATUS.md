# M4 Sprint Status — Mobile/PWA Hardening + Product Insights

Last updated: 2026-05-28

Tracking document for [`docs/M4_SPRINT_PLAN.md`](M4_SPRINT_PLAN.md).
Each sprint maps to a focused PR on `main`.

**Milestone completeness:** 🔄 In planning — M3.7 CI confirmation pending.

## Overview

| Sprint | Title                                            | Status  |
| ------ | ------------------------------------------------ | ------- |
| 0      | ADR & Scope Documentation                        | Pending |
| 1      | Entry Time Slots + Trend Smoothing               | Pending |
| 2      | Guided Onboarding + Cycle Tracking Groundwork    | Pending |
| 3      | Developer Mode: Phase Switcher + Onboarding Mock | Pending |
| 4      | PWA Hardening + Homescreen Install Prompt        | Pending |
| 5      | Visual QA, Docs & GitHub Closure                 | Pending |

## Prerequisites

- [ ] M3.7 CI — Web confirmation on `main` (Color System Hardening)

## Sprint 0 — Pending

- [ ] `docs/adr/0028-entry-time-slot-model.md` created
- [ ] `docs/adr/0029-trend-smoothing-frontend.md` created
- [ ] `docs/adr/0030-onboarding-tag-suggestions.md` created
- [ ] `docs/adr/0031-cycle-tracking-scope.md` created
- [ ] `docs/DESIGN_DOCUMENT.md` M4 scope note added

## Sprint 1 — Pending

- [ ] Alembic migration for `time_slot` field merged
- [ ] `TimeSlot` enum and Pydantic schemas updated
- [ ] `EntryForm` / `EntrySheet` chip group implemented
- [ ] Trend smoothing toggle live in Trends Mood tab
- [ ] SMA utility unit-tested
- [ ] CI green

## Sprint 2 — Pending

- [ ] Alembic migrations for `onboarding_completed_at` and `cycle_day` merged
- [ ] `GET /api/v1/onboarding/tag-suggestions` endpoint live
- [ ] `POST /api/v1/onboarding/complete` endpoint live
- [ ] `/onboarding` route activated with 3-step flow
- [ ] `cycle_day` field in `EntryForm` behind "+ More"
- [ ] Trends > Health tab cycle overlay implemented
- [ ] CI green

## Sprint 3 — Pending

- [ ] Dev Mode phase switcher section implemented
- [ ] Insight maturity override wired to insights store
- [ ] Onboarding preview modal implemented
- [ ] `devPhase` store resets on Dev Mode disable
- [ ] CI green

## Sprint 4 — Pending

- [ ] `pwaInstallStore` capturing `beforeinstallprompt`
- [ ] Install prompt banner on Home screen
- [ ] Service Worker offline fallback (`/offline`) added
- [ ] `manifest.webmanifest` verified
- [ ] iOS PWA meta tags present
- [ ] `docs/features/PWA.md` created
- [ ] CI green

## Sprint 5 — Pending

- [ ] `docs/quality/M4_VISUAL_QA.md` passed
- [ ] `docs/FRONTEND.md` updated
- [ ] `CHANGELOG.md` updated
- [ ] All M4 GitHub issues closed or rescoped
- [ ] CI — Web green on final `main` commit
