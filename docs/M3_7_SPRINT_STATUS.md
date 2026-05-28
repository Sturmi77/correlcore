# M3.7 Sprint Status - Color System Hardening

Last updated: 2026-05-28

Tracking document for [`M3_7_SPRINT_PLAN.md`](M3_7_SPRINT_PLAN.md). M3.7
formalizes the color token architecture from ADR-0026 and ADR-0027 without a
palette change or rebrand.

**Milestone completeness:** Release-complete locally. Rendered light-mode QA
passed on 2026-05-28; local Web gates are green. Upstream GitHub CI confirmation
is pending after push.

## Overview

| Sprint | Title                               | Status | Evidence                          |
| ------ | ----------------------------------- | ------ | --------------------------------- |
| 0      | ADR Documentation                   | Done   | ADR-0026, ADR-0027, concept docs  |
| 1      | Token Completion and Legacy Cleanup | Done   | `pnpm check:contrast`             |
| 2      | Light Mode QA Gate                  | Done   | `pnpm check:contrast`, Web CI job |

## Sprint 0 - ADR Documentation

- [x] `docs/adr/0026-color-scheme-evaluation-orange-vs-violet.md` exists.
- [x] `docs/adr/0027-light-mode-color-requirements.md` exists.
- [x] `docs/frontend/COLOR_SCHEME_CONCEPT.md` exists.
- [x] ADR README index includes ADR-0026 and ADR-0027.

## Sprint 1 - Token Completion and Legacy Cleanup

- [x] `--color-gold` exists in dark, light, and system dark fallback themes.
  - Dark: `#fbbf24`
  - Light: `#b45309` with 4.80:1 contrast on `#fafaf7`.
- [x] `--color-insight-early`, `--color-insight-provisional`, and
      `--color-insight-robust` exist in dark, light, and system dark fallback
      themes.
- [x] `--color-ms-primary*` aliases were removed from runtime token definitions.
- [x] Auth surfaces now use canonical `--color-primary`.
- [x] The system dark fallback block mirrors the `[data-theme='dark']` token
      block, including `--color-metric-*`, `--color-gold`, and
      `--color-insight-*`.

## Sprint 2 - Light Mode QA Gate

- [x] `pnpm check:contrast` exists and passes locally.
- [x] Web CI includes a dedicated `Contrast check` job.
- [x] `docs/FRONTEND.md` references ADR-0027 and
      `docs/frontend/COLOR_SCHEME_CONCEPT.md`.
- [x] `--color-text-faint` is excluded from informational contrast assertions
      and is documented as decorative-only.
- [x] Light-mode source scan limits `--color-text-faint` to decorative token
      definitions and placeholder styling.

## Local Verification

| Check                        | Result | Notes                                                |
| ---------------------------- | ------ | ---------------------------------------------------- |
| `pnpm check:contrast`        | Pass   | Dependency-free Node gate, no new npm packages added |
| Legacy primary alias search  | Pass   | No `color-ms-primary` references under `apps/`       |
| `--color-text-faint` scan    | Pass   | Remaining runtime use is placeholder styling only    |
| Rendered light-mode smoke QA | Pass   | 375px and 1280px, mocked auth/API, all M3.7 screens  |

## Light Mode QA Matrix

Automated rendered QA with mocked auth/API passed at 375px and 1280px viewports.
All inspected screens rendered in light mode with `--color-bg: #fafaf7`, visible
content, no Vite overlay, no page errors, and no horizontal text/control
overflow.

Screens covered by the QA runner:

- `/` (Home / Dashboard)
- `/entries/new` (Entry Sheet)
- `/insights` (Insights Feed)
- `/trends` (Trends)
- `/settings` (Settings)
- `/dev` (Developer View)

For each screen:

- [x] Text is legible in light mode.
- [x] Interactive elements retain visible focus styling.
- [x] Charts retain non-color differentiation through dash patterns or point
      shapes where rendered.
- [x] No `--color-ms-primary*` usage remains in primary screen source, and
      `--color-text-faint` is limited to placeholder/decorative styling.
- [x] `--color-text-faint` is not used for data labels.

## Acceptance Criteria

- [x] ADR-0026 and ADR-0027 merged to `main`.
- [x] `docs/frontend/COLOR_SCHEME_CONCEPT.md` exists.
- [x] `--color-gold` token present with verified contrast in both modes.
- [x] `--color-insight-early/provisional/robust` present in both modes.
- [x] No `--color-ms-primary*` tokens remain in codebase.
- [x] System-preference fallback block is complete.
- [x] `pnpm check:contrast` script passes locally and is wired into CI.
- [x] Primary screens QA'd in light mode at 375px and 1280px.
- [x] No WCAG AA violations found for informational text in light mode token
      assertions.
- [x] `docs/FRONTEND.md` references ADR-0027.
- [x] `CHANGELOG.md` updated.

## Follow-Up

- Confirm `CI - Web` is green on GitHub after push/PR.
