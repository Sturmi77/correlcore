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
- `/opt/cursor/artifacts/m7_mobile_after_fixes_demo.webm`
- `/opt/cursor/artifacts/m7_mobile_after_fixes_light.png`
- `/opt/cursor/artifacts/m7_mobile_after_fixes_dark.png`

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

- Remediated in follow-up: rotated heatmap column labels in symptom/tag patterns
  and tag patterns were replaced with compact horizontal mobile labels and more
  stable desktop spacing.
- Remediated in follow-up: symptom-history legend swatches received stronger
  minimum sizing and an inset contrast outline.
- Remediated in follow-up: forced-visualization mock co-occurrence data now
  differs across 30D/90D/1Y ranges.
- Remediated in follow-up: matrix export controls are hidden when no matrix rows
  are available, leaving the explicit empty state.
- Remediated in follow-up: mobile insight-card metadata now passes both `n` and
  `days`, defaulting to the 90-day insight context when no payload window exists.
- Remediated in follow-up: mobile filter tabs now scroll horizontally instead of
  wrapping into two disjoint rows.
- Remediated in follow-up: mobile M7 heatmaps use compact labels and wider local
  grid cells to reduce overlap and aggressive truncation.
- Remediated in follow-up: the mobile shared-entry sheet now accounts for
  safe-area bottom padding and constrains panel height with `dvh`.

## Follow-up Fixes (2026-05-31)

| Finding                    | Fix                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------------- |
| Card metadata placeholders | `InsightCard` passes `days` into `insights.card.sample_meta`, falling back to 90 days.      |
| Mobile filter wrapping     | `TabBar` uses no-wrap horizontal scrolling under 420 px.                                    |
| Heatmap label overlap      | Tag and symptom co-occurrence grids use compact mobile labels and clearer cell sizing.      |
| Bottom sheet safe area     | Co-occurrence entry sheet adds safe-area-aware panel padding and mobile height constraints. |
| Static demo range data     | Forced M7 mock co-occurrence data differs across 30D, 90D, and 1Y.                          |
| Symptom legend contrast    | Shared comparison heatmap legend cells have stronger sizing and inset contrast.             |
| Matrix empty state         | `InsightMatrix` hides export controls when no rows are present.                             |
| Regression coverage        | Added unit coverage for metadata/range mocks and an M7 mobile Playwright touch-flow smoke.  |

Post-fix manual spot check passed for card metadata, filter-tab layout, narrow
matrix alignment, and shared-entry sheet open/close behavior.

## Remaining Improvement Suggestions

1. Add component tests for `TagGroupsSection`, `SymptomAnalyticsSection`, and
   `SymptomCooccurrenceHeatmap` (tracked in Sprint 6).
2. ~~Add deterministic M7 demo seed tooling for 90+ entries~~ — **Done Sprint 5:**
   `backend/scripts/seed_m7_qa.py` (see [`M7_QUALITY_GATE.md`](M7_QUALITY_GATE.md)).

## Full-Stack QA with Seed (Sprint 5)

Use the deterministic QA user instead of developer mock visualizations:

```bash
cd backend
uv run --python 3.12 --extra dev --extra analytics python scripts/seed_m7_qa.py --reset
```

| Step         | Detail                                                             |
| ------------ | ------------------------------------------------------------------ |
| Login        | `m7-qa@localhost.dev` / `CorrectHorse123!`                                |
| Verify email | User is created verified; no Mailpit step required                 |
| `/insights`  | Disable „Force visualizations with mock data“ in Dev Mode          |
| Expect       | `symptom_cluster`, symptom co-occurrence, tag groups from live API |

Document GUI results in this file after an optional manual pass.

**Sprint 5 sign-off (2026-06-28):** Automated full-stack validation documented in
[`M7_SPRINT5_FULLSTACK_QA.md`](M7_SPRINT5_FULLSTACK_QA.md). CI runs
`test_m7_qa_seed_integration.py` on pgvector Postgres after migrations.
