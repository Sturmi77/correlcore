# M3.5 Sprint Status — Frontend Web and Mobile Optimisation

Last updated: 2026-05-16

Tracking document for [`M3_5_SPRINT_PLAN.md`](M3_5_SPRINT_PLAN.md). Each sprint maps to a focused PR on `main`.

**Milestone completeness:** ⚠️ Not complete for release tagging. Implementation and closeout documentation are present on `main`; the release image workflow has been verified green, but the M3.5 Definition of Done still requires rendered browser QA, GitHub issue closure/rescope from an authenticated session, and a green Web CI rerun after the local lint fixes in this closeout pass are committed.

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
- GitHub issue commenting/closure blocked in this agent environment because `gh` is not installed, no `GH_TOKEN` / `GITHUB_TOKEN` is present, and the browser session is not signed into GitHub
- Release workflow verified through the public GitHub API: `Release — Container Images` succeeded for `8274144` (`25965407416`)
- Web CI failure researched: `CI — Web` failed on `8274144` in typecheck/lint because `homeView.test.ts` had an unused `readable` import and `EntrySheet.svelte` had a stale `svelte-ignore`; both are fixed in this closeout pass and need a non-`[skip ci]` push to rerun
- Rendered browser QA remains pending outside the NAS/UNC agent environment because pnpm cannot create symlinks on the network share

## M3.5 GitHub Closure Matrix

| Issue | Closure decision | Evidence / action |
| --- | --- | --- |
| #170 | Close as implemented | Entry form sections and Home composition were delivered in Sprints 2-4; rendered QA still belongs to #186. |
| #171 | Close as implemented | Work-context hint and weekend auto-fill were delivered in Sprint 2. |
| #172 | Rescope to M7 | Sprint 3 chose Variant B: no manual sleep slider in M3.5; Health Connect remains the proper milestone. |
| #173 | Close as implemented | Sprint 8 delivered inactive tag lifecycle, hidden-tag filtering, reactivation, and inactive insight marking. |
| #182 | Close as implemented | Stress display inversion and metric semantics are covered by Sprint 2 and Trends work. |
| #183 | Close as implemented with scope note | Force visualizations exist in Settings developer controls with centralized mock data; placement differs from the original DEV-only wording. |
| #184 | Close as implemented | Sprint 5 delivered the readiness/progress meter; M3.6 now supersedes the broader maturity journey. |
| #185 | Close as implemented with scope note | DE/EN switching is implemented in Settings and persisted locally; not duplicated in header navigation. |
| #186 | Keep open until final release gate | Umbrella tracker should close only after Web CI rerun and rendered 375px / 768px / 1280px light/dark QA are complete. |

## M3.5 Definition of Done Audit

| Criterion                                                        | Status                      | Evidence / next action                                                                                                                                              |
| ---------------------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| All sprint PRs / commits merged to `main`                        | ✅ Met                      | Sprints 0-8 are done; Sprint 9 closeout commit is `fb65168` on `main`.                                                                                              |
| All M3.5 issues closed or deliberately rescoped                  | ⚠️ Closure prepared        | Public API confirms #170, #171, #172, #173, #182, #183, #184, #185, #186 remain open. Closure/rescope decisions are documented above; direct GitHub updates require an authenticated session. |
| `docs/FRONTEND.md` matches the implemented UI                    | ✅ Met for documented scope | Updated in Sprint 9 for screen model, trends tabs, settings sections, forced visualizations, and tag lifecycle.                                                     |
| `docs/M3_5_SPRINT_STATUS.md` documents final state               | ✅ Met                      | This audit records implementation status and remaining release blockers.                                                                                            |
| `CHANGELOG.md` contains M3.5                                     | ✅ Met                      | Sprints 1-9 are listed under Unreleased.                                                                                                                            |
| Local and GitHub CI gates green                                  | ⚠️ Fix prepared             | Public API shows `CI — Web` failed on `8274144` due two lint/typecheck findings; both are fixed locally. Backend pytest and local web pnpm/vitest remain blocked in this NAS/UNC agent environment. |
| Web and Mobile QA documented                                     | ⚠️ Documented, not executed | `docs/quality/M3_5_VISUAL_QA.md` records matrix and blocker; run rendered QA from local clone or CI runner.                                                         |
| No known 375px horizontal scroll / overlap / touch target issues | ⚠️ Needs rendered QA        | Static review did not identify a known issue, but viewport proof is still pending.                                                                                  |
| No No-Gamification violations in visible UI copy                 | ✅ Met by static evidence   | Locale regression test exists: `apps/web/src/lib/i18n/noGamificationCopy.test.ts`; visible copy uses "Tracking consistency".                                        |
| GitHub built new API and Web images after merge                  | ✅ Met                      | Public API verifies `Release — Container Images` succeeded for `8274144` in run `25965407416`.                                                                      |

## Next up

Commit and push the local Web CI lint fixes without `[skip ci]`, rerun rendered QA from a local clone or CI runner, then close/rescope the M3.5 GitHub issues according to the matrix above before tagging M3.5 as release-complete.
