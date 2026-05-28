# M4 Sprint Status — Quick Wins + Mobile/PWA Hardening

Last updated: 2026-05-28

Tracking document for [`docs/M4_SPRINT_PLAN.md`](M4_SPRINT_PLAN.md). M4 is
rescoped to quick wins and PWA/mobile hardening. Full Dexie offline sync,
sync conflict logs, Capacitor, Web Push, and Notes Composer are follow-ups
after M4.

**Milestone completeness:** Implementation complete locally; final GitHub CI
confirmation is still required after push/PR.

## Overview

| Sprint | Title                                | Status          |
| ------ | ------------------------------------ | --------------- |
| 0      | ADR & Scope Documentation            | Done            |
| 1      | Entry Slots + Trend Smoothing        | Done            |
| 2      | Guided Onboarding + Cycle Groundwork | Done            |
| 3      | Developer Mode                       | Done            |
| 4      | PWA Hardening                        | Done            |
| 5      | Closeout                             | In verification |

## Sprint 0 — Done

- [x] ADR-0028 documents existing `entries.slot` as the canonical time-slot field.
- [x] ADR-0029 documents client-side 7-day SMA smoothing.
- [x] ADR-0030 documents guided onboarding custom-tag creation by slug.
- [x] ADR-0031 documents neutral `cycle_day` scope.
- [x] `docs/DESIGN_DOCUMENT.md` reflects the M4 quick-win rescope.

## Sprint 1 — Done

- [x] `EntryUpdate.slot` accepted by backend schemas and service updates.
- [x] Slot-update uniqueness conflicts map to HTTP `409`.
- [x] Entry form/sheet exposes Morning / Noon / Evening chips behind `+ More`.
- [x] Delta lookup follows the selected slot.
- [x] Trends Mood has `Raw | Smoothed` for 30D+ ranges using `cc_trend_smooth`.
- [x] SMA edge cases are covered by unit tests.

## Sprint 2 — Done

- [x] Migration `013_add_cycle_day_to_entries.py` adds nullable `entries.cycle_day`.
- [x] Entry create/update/read schemas include `cycle_day` with `1..35` validation.
- [x] `GET /api/v1/onboarding/tag-suggestions` returns grouped suggestions.
- [x] `POST /api/v1/onboarding/complete` creates/reuses custom tags by slug and sets existing onboarding preferences.
- [x] `/onboarding` implements a 3-step guided flow with skip, tag picker, and summary.
- [x] Cycle day field is available behind `+ More`.
- [x] Trends Health shows neutral cycle-day context when data exists.

## Sprint 3 — Done

- [x] `devPhase` store is in-memory only.
- [x] Settings > Developer includes phase switcher, onboarding-state toggle, and entry-count mock.
- [x] Insight store reads Dev Mode maturity overrides when visual mocks are forced.
- [x] Onboarding preview opens from Settings in a modal iframe.
- [x] Disabling Dev Mode resets all overrides.

## Sprint 4 — Done

- [x] `pwaInstallStore` captures `beforeinstallprompt`.
- [x] Home shows a dismissible install banner persisted via `cc_pwa_dismissed`.
- [x] `/offline` fallback route added.
- [x] Service Worker caches app shell/static resources and skips `/api/*`.
- [x] Manifest, app icon, and iOS PWA meta tags reviewed.
- [x] `docs/features/PWA.md` documents install/offline behavior.

## Sprint 5 — In Verification

- [x] `docs/FRONTEND.md` updated for M4 user-visible surfaces.
- [x] `CHANGELOG.md` updated under Unreleased.
- [x] `docs/quality/M4_VISUAL_QA.md` created with local QA status.
- [ ] Final local gates green; reruns currently blocked by sandbox access to
      `.svelte-kit`, `vite.config.ts`, and the `uv` cache.
- [ ] GitHub issues #10, #24, #27, and #200 commented/rescoped; connector
      startup was unavailable during local closeout.
- [ ] GitHub CI green after push/PR.
      | Sprint | Title | Status |
      | ------ | ------------------------------------------------ | ------- |
      | 0 | ADR & Scope Documentation | Pending |
      | 1 | Entry Time Slots + Trend Smoothing | Pending |
      | 2 | Guided Onboarding + Cycle Tracking Groundwork | Pending |
      | 3 | Developer Mode: Phase Switcher + Onboarding Mock | Pending |
      | 4 | PWA Hardening + Homescreen Install Prompt | Pending |
      | 5 | Visual QA, Docs & GitHub Closure | Pending |

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
