# M5 Notes — Tag Co-Occurrence Heatmap

Last updated: 2026-05-28

This document captures the scope and acceptance criteria for the
co-occurrence heatmap feature deferred from M4.

## Context

The M3.5 tag heatmap shows **frequency** (how often a tag appears).
This feature extends that with a **co-occurrence** view: how often two
tags appear on the same entry, visualised as a Tag × Tag matrix.

Delayed to M5 because it requires a meaningful data volume to be
useful, and a new backend aggregation endpoint.

## Scope

### Sprint 1 — Backend: Co-Occurrence Endpoint

- `GET /api/v1/insights/tag-cooccurrence`
  - Query params: `range` (30d | 90d | 1y), `min_count` (default 2)
  - Returns: list of `{ tag_a, tag_b, count, pct_of_a, pct_of_b }`
  - Only includes pairs where both tags are active
  - Hidden tags excluded
  - Sorted by `count` descending
- Unit tests: pair counting, hidden-tag exclusion, range filtering
- `docs/API.md` updated

### Sprint 2 — Frontend: 2D Heatmap Component

- New component `TagCooccurrenceHeatmap.svelte`
  - Axes: Tag A (rows) × Tag B (columns)
  - Cell colour: intensity mapped to `count` using `--color-primary`
    alpha scale (0 = transparent, max = full opacity)
  - Cells are interactive: tap/click opens Entry History sheet filtered
    to entries containing both tags (reuses M3.5 Entry History sheet)
  - Empty state when fewer than 5 tag pairs exist
- Placed in Insights page under a new "Patterns" section
- Range control: 30D / 90D / 1Y
- i18n keys `insights.cooccurrence.*`
- Component tests: render, cell interaction, empty state

## Acceptance Criteria

- [ ] `GET /api/v1/insights/tag-cooccurrence` returns correct pair counts
- [ ] Matrix renders with correct colour intensity
- [ ] Tapping a cell opens Entry History filtered to both tags
- [ ] Empty state shown when data is insufficient
- [ ] Hidden tags never appear on either axis
- [ ] Visual QA at 375 px, 768 px, 1280 px (light + dark)
- [ ] CI green

## Prerequisites

- M4 complete (stable tag model, Entry History sheet reusable)
- At least one user with ≥ 30 entries in staging for manual QA

## Deferred

Clustering / pattern recognition (automatic grouping) is deferred to
M8. M5 delivers only the raw co-occurrence view without algorithmic
interpretation.
