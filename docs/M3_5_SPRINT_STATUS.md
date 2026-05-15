# M3.5 Sprint Status — Frontend Web and Mobile Optimisation

Last updated: 2026-05-15

Tracking document for [`M3_5_SPRINT_PLAN.md`](M3_5_SPRINT_PLAN.md). Each sprint maps to a focused PR on `main`.

## Overview

| Sprint | Title                                     | Status  | PR / commit (main)   | Issues           |
| ------ | ----------------------------------------- | ------- | -------------------- | ---------------- |
| 0      | Repo Hygiene & Design-System Alignment    | ✅ Done | #187 / `1152d13`     | #186 (partial)   |
| 1      | App Shell & Mobile Navigation             | ✅ Done | `64735bc`, `fc25c80` | #186             |
| 2      | Entry Flow Foundation                     | ✅ Done | `830d31a`            | #170, #171, #182 |
| 3      | Entry Bottom Sheet & Sleep Quality        | ✅ Done | (pending push)       | #172, #186       |
| 4      | Home Screen Recomposition                 | ⬜ Open | —                    | #186             |
| 5      | Insights Quality & Progressive Disclosure | ⬜ Open | —                    | #184, #186       |
| 6      | Trends Tabbed Analysis Surface            | ⬜ Open | —                    | #182, #186       |
| 7      | Settings, Language & Developer UX         | ⬜ Open | —                    | #183, #185, #186 |
| 8      | Tag Lifecycle & Inactive Correlations     | ⬜ Open | —                    | #173             |
| 9      | Visual QA, Docs & GitHub Closure          | ⬜ Open | —                    | all              |

## Sprint 0 — Done

- `@eaDir` / `SYNOINDEX_MEDIA_INFO` removed; `.gitignore` updated
- Violet primary tokens + ADR-0020
- `FRONTEND.md` i18n guidance (`svelte-i18n` for M3.5)

## Sprint 1 — Done

- Bottom navigation (4 primary screens) + side nav ≥768px
- Skip link → `#main-content`
- `AppNav.svelte`, `appNav.ts` routing helpers
- Hidden on `/auth/*`, `/status`, `/onboarding/*`
- Lucide icons via package exports (build-safe)

## Sprint 2 — Done (`830d31a`)

**PR / commit:** `830d31a` on `main` — `feat(web): M3.5 sprint 2 — entry flow foundation`

- Entry form split into labelled sections (date, metrics, work context, tags, symptoms, note, delta)
- Work-context hint (informative, non-blocking) + weekend auto-fill via `defaultWorkContextForDate`
- `src/lib/config/metrics.ts` + `src/lib/utils/metrics.ts` (stress `invert`, display `6 - raw`)
- `MetricTimeseries` chart Y-axis uses display values for `stress_avg`
- `ScaleSlider` stress legend (relaxed ↔ very stressed)
- Backend: `display_metric_value()` in `insight_engine.py` (view-layer only; DB raw unchanged)
- Unit tests: `workContext`, `metrics`, `ScaleSlider`, `charts` stress inversion

## Sprint 3 — Done

**Sleep quality (#172):** **Variant B** — deferred to M7 (Health Connect). `sleep_quality` stays in `metrics.ts` only; no Alembic migration in M3.5.

- `EntryForm.svelte` — shared form (page + sheet modes)
- `EntrySheet.svelte` — bottom sheet (&lt;768px) / centered modal (≥768px)
- Home CTA opens sheet; `/entries/new` deep link uses `EntryForm` in page mode
- Tags, symptoms, note behind “+ More” in sheet mode
- Escape, backdrop, close button, focus restore, dirty-close confirm
- `EntrySheet.test.ts` — open/close/backdrop

## Next up — Sprint 4

Home screen recomposition (max. 3 information zones per ADR-0017).
