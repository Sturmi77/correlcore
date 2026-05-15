# M3.5 Sprint Status — Frontend Web and Mobile Optimisation

Last updated: 2026-05-15

Tracking document for [`M3_5_SPRINT_PLAN.md`](M3_5_SPRINT_PLAN.md). Each sprint maps to a focused PR on `main`.

## Overview

| Sprint | Title                                     | Status  | PR / commit (main)   | Issues           |
| ------ | ----------------------------------------- | ------- | -------------------- | ---------------- |
| 0      | Repo Hygiene & Design-System Alignment    | ✅ Done | #187 / `1152d13`     | #186 (partial)   |
| 1      | App Shell & Mobile Navigation             | ✅ Done | `64735bc`, `fc25c80` | #186             |
| 2      | Entry Flow Foundation                     | ✅ Done | (this sprint)        | #170, #171, #182 |
| 3      | Entry Bottom Sheet & Sleep Quality        | ⬜ Open | —                    | #172, #186       |
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

## Sprint 2 — Done

- Entry form split into labelled sections (date, metrics, work context, tags, symptoms, note, delta)
- Work-context hint (informative, non-blocking) + weekend auto-fill via `defaultWorkContextForDate`
- `src/lib/config/metrics.ts` + `src/lib/utils/metrics.ts` (stress `invert`, display `6 - raw`)
- `MetricTimeseries` chart Y-axis uses display values for `stress_avg`
- `ScaleSlider` stress legend (relaxed ↔ very stressed)
- Unit tests: `workContext`, `metrics`, `ScaleSlider`

## Next up — Sprint 3

Entry as bottom sheet from Home; `#172` sleep-quality decision (Variant A vs B per plan).
