# M3.5 Sprint Status — Frontend Web and Mobile Optimisation

Last updated: 2026-05-16

Tracking document for [`M3_5_SPRINT_PLAN.md`](M3_5_SPRINT_PLAN.md). Each sprint maps to a focused PR on `main`.

**Milestone completeness:** ⚠️ Not complete for release tagging. Implementation and closeout documentation are present on `main`, but the M3.5 Definition of Done still requires rendered browser QA, GitHub issue closure/rescope, executable CI confirmation, and release image verification.

## Overview

| Sprint | Title                                     | Status             | PR / commit (main)   | Issues           |
| ------ | ----------------------------------------- | ------------------ | -------------------- | ---------------- |
| 0      | Repo Hygiene & Design-System Alignment    | ✅ Done            | #187 / `1152d13`     | #186 (partial)   |
| 1      | App Shell & Mobile Navigation             | ✅ Done            | `64735bc`, `fc25c80` | #186             |
| 2      | Entry Flow Foundation                     | ✅ Done            | `830d31a`            | #170, #171, #182 |
| 3      | Entry Bottom Sheet & Sleep Quality        | ✅ Done            | `bea8b40`            | #172, #186       |
| 4      | Home Screen Recomposition                 | ✅ Done            | `9a02655`            | #186             |
| 5      | Insights Quality & Progressive Disclosure | ✅ Done            | `da5e74f`            | #184, #186       |
| 6      | Trends Tabbed Analysis Surface            | ✅ Done            | `6173c80`            | #182, #186       |
| 7      | Settings, Language & Developer UX         | ✅ Done            | `a30cf6e`            | #183, #185, #186 |
| 8      | Tag Lifecycle & Inactive Correlations     | ✅ Done            | `0d255f0`            | #173             |
| 9      | Visual QA, Docs & GitHub Closure          | ⚠️ Closure Pending | `fb65168`            | all              |

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

## Sprint 4 — Done

- Home reduced to **3 zones**: today context, insight preview, 7-day sparkline + CTA
- Removed from Home: `InsightMatrix`, `HomeRecentEntries`, `HomeSummary`, `InsightConfidenceScale`, `WeekdayPatternChart`
- New `HomeTodayContext.svelte` (date, work context badge, entry status)
- Secondary links to Insights and Trends
- `homeView.test.ts` + `HomeTodayContext.test.ts`

## Sprint 5 — Done

- `InsightQualityMeter.svelte` added to the Insights feed
- `estimateInsightReadiness` estimates first-insight readiness from day-entry dates
- 0-3 entries: neutral collection copy, no estimate
- 4-29 entries: `X/30` plus a 14-day tracking-pace estimate when recent data exists
- 4-29 without recent entries: no time estimate
- 30+ entries: first-insight/full-insights stages with confidence label context
- `/insights` now loads entries for the existing 90-day feed context and derives readiness without a separate meter-only endpoint
- DE/EN copy stays descriptive: no imperative wording, emoji, or urgency framing
- Tests: `insightQuality`, `InsightQualityMeter`, and `InsightFeed` coverage

## Sprint 6 — Done

- `/trends` converted to Mood / Activities / Health tabs
- Unified range controls now expose 7D / 30D / 90D / 1Y
- Backend and web stats ranges now include `quarter` for 90-day daily points
- Mood data points and activity heatmap cells open a read-only Entry History sheet
- Health tab avoids unfinished charts and shows neutral readiness / tracking-consistency copy
- Tests: tab switching, Entry History sheet, and 90-day backend range coverage

## Sprint 7 — Done (`a30cf6e`)

- Settings split into TRACKING / ANALYSIS / PRIVACY & DATA / APPEARANCE / DEVELOPER
- Language segmented control (`DE | EN`) persists via localStorage and updates `svelte-i18n` without reload
- Dev Mode store now includes `devForceVisualizations` with `dev_force_viz` persistence
- Disabling Dev Mode resets Force Visualizations
- Force Visualizations uses centralized mock entries, insights, and trends without API writes

## Sprint 8 — Done (`0d255f0`)

- Tag settings split active and inactive tags while loading `include_hidden=true`
- Inactive tags can be reactivated without removing historical entry relations
- Entry picker/store paths keep hidden tags out of new assignments
- Tag heatmap and insight generation skip hidden tags for new calculations
- Existing tag insights remain visible and are marked when their tag is inactive
- API docs clarify `include_hidden` and hidden-tag calculation behavior

## Sprint 9 — Closure Pending (`fb65168`)

- Visual QA closeout recorded in `docs/quality/M3_5_VISUAL_QA.md`
- `docs/FRONTEND.md` reconciled with implemented M3.5 screens and tag lifecycle
- Changelog includes Sprint 9 closeout and QA handoff
- GitHub issue states checked via public API: #170, #171, #172, #173, #182, #183, #184, #185, #186 remain open
- GitHub issue commenting/closure blocked in this agent environment because `gh` is not installed
- Rendered browser QA remains pending outside the NAS/UNC agent environment because pnpm cannot create symlinks on the network share

## M3.5 Definition of Done Audit

| Criterion                                                        | Status                      | Evidence / next action                                                                                                                                              |
| ---------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| All sprint PRs / commits merged to `main`                        | ✅ Met                      | Sprints 0-8 are done; Sprint 9 closeout commit is `fb65168` on `main`.                                                                                              |
| All M3.5 issues closed or deliberately rescoped                  | ❌ Open                     | #170, #171, #172, #173, #182, #183, #184, #185, #186 were still open when checked via GitHub API. Close implemented items; rescope #172 to M7 if still intentional. |
| `docs/FRONTEND.md` matches the implemented UI                    | ✅ Met for documented scope | Updated in Sprint 9 for screen model, trends tabs, settings sections, forced visualizations, and tag lifecycle.                                                     |
| `docs/M3_5_SPRINT_STATUS.md` documents final state               | ✅ Met                      | This audit records implementation status and remaining release blockers.                                                                                            |
| `CHANGELOG.md` contains M3.5                                     | ✅ Met                      | Sprints 1-9 are listed under Unreleased.                                                                                                                            |
| Local and GitHub CI gates green                                  | ⚠️ Partially verified       | Local `git diff --check` for Sprint 9 passed after rebase. Backend pytest and web pnpm/vitest remain blocked in this NAS/UNC agent environment; confirm via CI.     |
| Web and Mobile QA documented                                     | ⚠️ Documented, not executed | `docs/quality/M3_5_VISUAL_QA.md` records matrix and blocker; run rendered QA from local clone or CI runner.                                                         |
| No known 375px horizontal scroll / overlap / touch target issues | ⚠️ Needs rendered QA        | Static review did not identify a known issue, but viewport proof is still pending.                                                                                  |
| No No-Gamification violations in visible UI copy                 | ✅ Met by static evidence   | Locale regression test exists: `apps/web/src/lib/i18n/noGamificationCopy.test.ts`; visible copy uses "Tracking consistency".                                        |
| GitHub built new API and Web images after merge                  | ⚠️ Needs verification       | Verify release/image workflow after the latest `main` push.                                                                                                         |

## Next up

Run rendered QA from a local clone or CI runner, then close/rescope the remaining M3.5 GitHub issues.
