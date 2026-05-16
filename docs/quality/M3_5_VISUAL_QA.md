# M3.5 Visual QA Closeout

Date: 2026-05-16

Scope: M3.5 frontend and mobile optimisation across Home, Entry Sheet, Insights, Trends, Settings, and Tag Settings.

## Result

M3.5 is code-complete on `main` through Sprint 8 (`0d255f0`). Sprint 9 records the final QA and documentation closeout. In this Cursor environment, rendered browser QA could not be executed because the web toolchain still fails on the NAS UNC path with pnpm symlink errors; the remote CI/image build remains the source of truth for executable web gates.

## Static QA Evidence

- Home, Insights, Trends, Settings, and Tag Settings have loading/error/empty/populated handling either directly or through their child components.
- Forced visualizations are available through Settings developer unlock and central mock data for Home, Insights, and Trends.
- Icon-only controls expose `aria-label` strings: theme toggles, insight disclaimer/dismiss controls, modal/sheet close controls, trend chart points, and heatmap cells.
- No-gamification copy is covered by `apps/web/src/lib/i18n/noGamificationCopy.test.ts`; visible copy uses "Tracking consistency" instead of streak/reward framing.
- `docs/FRONTEND.md` has been reconciled with the implemented M3.5 screen model: Insights quality meter, Mood/Activities/Health trends tabs, Settings sections, developer force visualizations, and inactive tag lifecycle.

## Viewport Matrix

| Viewport | Intended Coverage | Status |
| --- | --- | --- |
| 375 x 812 | Mobile bottom nav, Entry Sheet, stacked settings/tag rows, no horizontal scroll | Requires rendered browser pass |
| 768 x 1024 | Tablet side nav breakpoint and sheet/modal transitions | Requires rendered browser pass |
| 1280 x 800 | Desktop layout, trends charts, settings sections, insight feed density | Requires rendered browser pass |

## Theme Matrix

| Theme | Intended Coverage | Status |
| --- | --- | --- |
| Light | Surface/card contrast, focus rings, chart/heatmap colors | Requires rendered browser pass |
| Dark | Surface/card contrast, focus rings, chart/heatmap colors | Requires rendered browser pass |

## State Matrix

| State | Coverage |
| --- | --- |
| Loading | Insight cards, quality meter, trends charts/heatmap, tag settings |
| Error | Insight feed retry, tag settings alert, component-level chart/tag errors |
| Empty | Insight feed empty state, Entry History empty date, Tag Settings active/inactive empty groups |
| Populated | Home mock entries, insight feed, trends charts/heatmap, settings sections |
| Forced visualizations | Dev Mode -> Force visualizations feeds centralized mock entries, insights, and trends |

## Core Interactions

| Interaction | Implementation Evidence | Rendered QA |
| --- | --- | --- |
| Home -> Entry Sheet -> Auto-Save -> Day Delta | `EntrySheet`, `EntryForm`, `SaveStatusBadge`, `DayDeltaCard` tests/util coverage | Pending browser pass |
| Insights -> Filter -> Disclaimer -> Details | `InsightFeed`, `CorrelationDisclaimer`, `InsightCard` tests | Pending browser pass |
| Trends -> Tab -> Data point -> Entry History Sheet | `routes/trends/page.test.ts`, `EntryHistorySheet.test.ts` | Pending browser pass |
| Settings -> Language -> Theme -> Dev Unlock -> Force Viz | `routes/settings/page.test.ts`, `devMode.test.ts` | Pending browser pass |
| Tag Settings -> deactivate/reactivate -> picker hidden tags | `routes/settings/tags/page.test.ts`, `tags.test.ts`, backend tag tests | Pending browser pass |

## Tooling Blockers

- `gh` is not installed in this shell, so GitHub issues could not be commented or closed from the agent.
- `pytest` is not installed in the active Python environment.
- `pnpm`/Vitest cannot install/run from the NAS UNC workspace because pnpm fails while creating project symlinks in the store.

## Follow-Up Before Release Tag

- Run the rendered QA matrix from a local clone or CI environment where `pnpm install` succeeds.
- Close or rescope M3.5 GitHub issues after posting the closeout summary from this document.
- Verify the GitHub Actions image build for `correlcore-api` and `correlcore-web` after the pushed Sprint 9 commit.
