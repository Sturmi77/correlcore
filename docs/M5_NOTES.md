# M5.1 Notes - Tag Co-Occurrence Heatmap

Last updated: 2026-05-28

This document captures the scope and acceptance criteria for the co-occurrence
heatmap feature deferred from M4 and then moved out of the official M5 exit
criteria. M5 now delivers Habits Core without gamification; this feature is a
M5.1/backlog quick win.

## Context

The M3.5 tag heatmap shows **frequency**: how often a tag appears. This feature
extends that with a **co-occurrence** view: how often two tags appear on the
same entry, visualised as a Tag x Tag matrix.

Delayed beyond M5 because it requires a meaningful data volume to be useful and
a new backend aggregation endpoint. It should not block M5 Habits Core.

## Scope

### Sprint 1 - Backend: Co-Occurrence Endpoint

- `GET /api/v1/insights/tag-cooccurrence`
  - Query params: `range` (`30d | 90d | 1y`), `min_count` (default 2)
  - Returns: list of `{ tag_a, tag_b, count, pct_of_a, pct_of_b }`
  - Only includes pairs where both tags are active
  - Hidden tags excluded
  - Sorted by `count` descending
- Unit tests: pair counting, hidden-tag exclusion, range filtering
- `docs/API.md` updated

### Sprint 2 - Frontend: 2D Heatmap Component

- New component `TagCooccurrenceHeatmap.svelte`
  - Axes: Tag A rows x Tag B columns
  - Cell colour: intensity mapped to `count` using `--color-primary` alpha scale
  - Cells are interactive: tap/click opens Entry History sheet filtered to
    entries containing both tags
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

- M5 complete (stable habit/tag model and Entry History sheet reusable)
- At least one user with >= 30 entries in staging for manual QA

## Deferred

Clustering / pattern recognition is deferred to M7. M5.1 delivers only the raw
co-occurrence view without algorithmic interpretation.
