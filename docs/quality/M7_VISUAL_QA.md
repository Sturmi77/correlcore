# M7 Visual QA Closeout

Date: 2026-05-31

Scope: Full GUI smoke pass with focus on **M7 Insights v2** on `/insights`
(symptom analytics, symptom/tag co-occurrence, tag groups, matrix/feed views).

## Result

**M7 GUI QA: passed with follow-up recommendations.**

No critical blocker was found. The authenticated GUI loads, core navigation works,
and the M7 insight surfaces render and respond with forced visualization mock
data. The backend M7 services and frontend gates pass. The remaining items are
visual polish and coverage gaps, not functional blockers.

Primary walkthrough artifact:

- `/opt/cursor/artifacts/m7_insights_page_video.webm`

Responsive screenshots:

- `/opt/cursor/artifacts/m7_insights_light_375.png`
- `/opt/cursor/artifacts/m7_insights_light_768.png`
- `/opt/cursor/artifacts/m7_insights_light_1280.png`
- `/opt/cursor/artifacts/m7_insights_dark_375.png`
- `/opt/cursor/artifacts/m7_insights_dark_768.png`
- `/opt/cursor/artifacts/m7_insights_dark_1280.png`

Mobile follow-up artifacts:

- `/opt/cursor/artifacts/m7_mobile_insights_demo_v2.webm`
- `/opt/cursor/artifacts/m7_mobile_insights_light_390.png`
- `/opt/cursor/artifacts/m7_mobile_insights_dark_390_v2.png`
- `/opt/cursor/artifacts/m7_mobile_card_meta_bug.png`

## Test Environment

| Area     | Detail                                                            |
| -------- | ----------------------------------------------------------------- |
| Web      | Local Vite dev server at `http://localhost:5173`                  |
| API      | Local FastAPI server at `http://127.0.0.1:8000`                   |
| Services | PostgreSQL 16 pgvector, Redis 7, Mailpit                          |
| Data     | QA user plus developer mode `Force visualizations with mock data` |
| M7 phase | Robust mock state                                                 |

## GUI Coverage

| Route / surface | Result | Notes                                                                          |
| --------------- | ------ | ------------------------------------------------------------------------------ |
| `/auth/login`   | Pass   | QA user login worked after email verification through Mailpit.                 |
| `/`             | Pass   | Authenticated shell and onboarding state render for a new user.                |
| `/entries/new`  | Pass   | Entry form and autosave surface render; existing smoke test covers write path. |
| `/trends`       | Pass   | Trends chart, compare panel, and health tab render in smoke.                   |
| `/settings`     | Pass   | Developer mode activation and force visualization controls work.               |
| `/insights`     | Pass   | M7 widgets render with mock data and core interactions work.                   |

## M7 Interaction Matrix

| Feature                   | Result | Evidence                                                               |
| ------------------------- | ------ | ---------------------------------------------------------------------- |
| Robust maturity header    | Pass   | Header shows Phase 4 / Robust Insights with 42 entries.                |
| Findings view             | Pass   | Default feed renders M7 mock cards.                                    |
| Symptoms tab              | Pass   | Symptom-only feed filtering is clickable and renders symptom findings. |
| Matrix view               | Pass   | Correlation Matrix view opens and returns to Findings.                 |
| Blend in symptoms toggle  | Pass   | Checkbox toggles off/on and updates the section visibility.            |
| Symptom history           | Pass   | Symptom heatmap section renders under `Symptoms in insights`.          |
| Symptom + tag patterns    | Pass   | Co-occurrence matrix renders with lift/count content.                  |
| Tag groups                | Pass   | Three mock tag groups render with strength labels.                     |
| Tag co-occurrence ranges  | Pass   | 30D/90D/1Y controls update active state.                               |
| Co-occurrence entry sheet | Pass   | Clicking a populated tag-pair grid cell opens shared entries.          |

## Viewport Matrix

| Viewport   | Light | Dark | Notes                                                     |
| ---------- | ----- | ---- | --------------------------------------------------------- |
| 390 x 844  | Pass  | Pass | iPhone-sized touch flow works; visual issues below.       |
| 375 x 812  | Pass  | Pass | Content stacks; horizontal heatmap scrolling is required. |
| 768 x 1024 | Pass  | Pass | Side-nav/tablet density remains usable.                   |
| 1280 x 800 | Pass  | Pass | Desktop layout is readable and complete.                  |

## Mobile Follow-up

The mobile pass used an iPhone-sized Playwright device profile with touch input.
Bottom navigation, M7 feed filters, matrix/findings switching, the symptom
blend toggle, symptom analytics, tag groups, range controls, and the shared-entry
bottom sheet all responded.

| Mobile interaction            | Result | Notes                                              |
| ----------------------------- | ------ | -------------------------------------------------- |
| Bottom nav: Insights ↔ Trends | Pass   | Touch targets navigate and preserve auth state.    |
| Symptoms feed tab             | Pass   | Symptom card filter responds on mobile.            |
| Matrix / Findings toggle      | Pass   | Both views can be reached via touch.               |
| Blend in symptoms checkbox    | Pass   | Off/on states update correctly.                    |
| Symptom analytics section     | Pass   | Section renders, but dense table labels are tight. |
| Tag groups                    | Pass   | Groups render in stacked mobile flow.              |
| Patterns range controls       | Pass   | `1Y` active state updates after tap.               |
| Co-occurrence entry sheet     | Pass   | Opens and closes from a heatmap cell.              |

## Static and Automated Gates

| Gate                                           | Result                                                                                                                                |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `pnpm lint`                                    | Pass: `svelte-check found 0 errors and 0 warnings`.                                                                                   |
| `pnpm typecheck`                               | Pass: `svelte-check found 0 errors and 0 warnings`.                                                                                   |
| `pnpm test`                                    | Pass: 83 files / 418 tests passed.                                                                                                    |
| `pnpm --filter @correlcore/web test:e2e:smoke` | Pass after installing missing Playwright Chromium: 3 tests passed.                                                                    |
| `pnpm build`                                   | Pass: SvelteKit production build completed.                                                                                           |
| `pnpm check:contrast`                          | Pass: contrast check passed.                                                                                                          |
| `uv run --python 3.12 ruff check .`            | Pass.                                                                                                                                 |
| Targeted M7 backend pytest subset              | Functional pass: 53 tests passed; subset command exits non-zero because global coverage is below the repo threshold for partial runs. |
| `uv run --python 3.12 pytest`                  | Pass: 446 passed, 1 skipped, coverage 94.18%.                                                                                         |

## Findings

### Functional

- No M7 functional blocker found in the tested mock-data GUI path.
- The existing Playwright smoke test does not cover M7-specific endpoints or UI
  widgets; it only proves a basic `/insights` feed render.
- The full-stack real-data M7 path still needs a seed or fixture workflow for
  90+ entries to validate Lasso, lag, and clustering without developer mock data.

### Visual / UX

- Rotated heatmap column labels in symptom/tag patterns and tag patterns appear
  visually detached from their columns, especially in dense desktop layouts.
- The symptom-history legend is too faint; color swatches are difficult to see in
  the recorded light-theme pass.
- Changing tag co-occurrence range updates the active control, but mock data
  stays unchanged. This is acceptable for static mock data but can look broken
  during demos.
- Matrix empty state can look sparse when symptom blending is disabled because
  the matrix heading/export button remain while the matrix content is absent.
- Mobile insight-card metadata renders the untranslated placeholders
  `Based on {n} entries · {days} days`; the card currently passes only `n` into a
  string that also expects `days`.
- Mobile filter pills can wrap awkwardly into two rows when horizontal space is
  tight.
- Mobile M7 heatmaps are functional but cramped: rotated column headers overlap
  or float away from their columns, and symptom/tag labels truncate aggressively.
- The mobile shared-entry bottom sheet works, but its backdrop/safe-area spacing
  can appear as an oversized grey block at the bottom of the viewport.

## Improvement Suggestions

1. Add a dedicated M7 Playwright spec that mocks:
   `/insights/tag-clusters`, `/insights/symptom-tag-cooccurrence`,
   `/insights/tag-cooccurrence`, `/entries/stats/symptoms`, and M7 insight cards
   in `/insights/latest`.
2. Add component tests for `TagGroupsSection`, `SymptomAnalyticsSection`, and
   `SymptomCooccurrenceHeatmap`.
3. Add deterministic M7 demo seed tooling for 90+ entries so full-stack GUI QA
   can run without developer mock visualizations.
4. Improve heatmap header spacing and legend contrast for symptom/tag and tag
   co-occurrence matrices.
5. Make mock range data visibly differ by range or show a small "demo data"
   note when forced visualizations are enabled.
6. Replace the sparse matrix empty gap with an explicit empty state when filters
   or symptom blending leave no matrix rows.
7. Fix insight-card metadata interpolation by passing the expected `days` value
   or changing the locale string to match available data.
8. Add a mobile-specific layout treatment for insight feed tabs and dense
   co-occurrence matrices, such as horizontal tab scrolling and clearer
   small-screen header alignment.
