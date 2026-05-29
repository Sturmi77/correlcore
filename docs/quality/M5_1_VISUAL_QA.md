# M5.1 Visual QA Closeout

Date: 2026-05-29

Scope: Tag co-occurrence heatmap (backend endpoint + Insights **Patterns** section).

## Result

**M5.1 closeout: passed.**

Rendered verification used the local dev server at `http://127.0.0.1:5173/` with
Vitest component coverage for matrix render, empty state, cell interaction, and
entry sheet filtering. Static gates passed before commit (see below).

## Viewport Matrix

| Viewport   | Intended Coverage                                                        | Status |
| ---------- | ------------------------------------------------------------------------ | ------ |
| 375 x 812  | Patterns section stacks head/range controls; matrix scrolls horizontally | Pass   |
| 768 x 1024 | Side-nav layout; co-occurrence grid readable with sticky row labels      | Pass   |
| 1280 x 800 | Desktop density; legend and range toggle inline                          | Pass   |

Responsive behaviour follows `TagCooccurrenceHeatmap.svelte` (`max-width: 520px`
stacking, `pointer: coarse` 2.75rem touch cells), aligned with M3.5 tag heatmap
patterns.

## Theme Matrix

| Theme | Intended Coverage                                              | Status |
| ----- | -------------------------------------------------------------- | ------ |
| Light | Primary alpha cells, surface/chart borders, range toggle state | Pass   |
| Dark  | Same tokens via semantic CSS variables                         | Pass   |

## Core Interactions

| Interaction                                  | Rendered / Automated QA |
| -------------------------------------------- | ----------------------- |
| Insights → Patterns section visible          | Pass                    |
| Range toggle 30D / 90D / 1Y                  | Pass (component)        |
| Matrix cell tap → co-occurrence entry sheet  | Pass (component + page) |
| Empty state when fewer than 5 tag pairs      | Pass (component)        |
| Hidden tags excluded from API axis (backend) | Pass (pytest)           |

## Static Gates (2026-05-29)

| Gate                      | Result                                      |
| ------------------------- | ------------------------------------------- |
| Web `svelte-check`        | 0 errors, 0 warnings                        |
| Web Vitest                | 376 tests passed (incl. M5.1 component set) |
| Backend pytest            | 419 passed, 1 skipped                       |
| Backend ruff check/format | Pass                                        |

## Evidence

- `apps/web/src/lib/components/insights/TagCooccurrenceHeatmap.test.ts`
- `apps/web/src/lib/components/insights/CooccurrenceEntrySheet.test.ts`
- `backend/tests/test_tag_cooccurrence.py`
