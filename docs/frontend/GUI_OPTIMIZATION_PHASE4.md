# CorrelCore — GUI Optimization Phase 4

**Date:** 2026-07-11  
**Predecessor:** Phase 3 — [`GUI_OPTIMIZATION_PHASE3.md`](GUI_OPTIMIZATION_PHASE3.md) (O-43–O-56)  
**Source:** Mobile UX findings (Home, Erkenntnisse, Trends)

Phase 4 targets **mobile correctness** and **interpretability** for chart-heavy screens: single Home CTA, weekday overview, sparse heatmap pruning, Trends sticky chrome, and Insights overflow fixes.

---

## Issue index (O-57 – O-62)

| ID   | Sprint | Impact   | Effort | Status | Title                                                        |
| ---- | ------ | -------- | ------ | ------ | ------------------------------------------------------------ |
| O-57 | P4-D   | High     | Low    | Open   | Home: single primary CTA when today has no entry             |
| O-58 | P4-D   | High     | Medium | Open   | Home: weekday overview with per-day findings (7 columns)     |
| O-59 | P4-B   | Medium   | Medium | Done   | Heatmaps: hide empty rows in selected range (all viewports; bucket-aware) |
| O-60 | P4-C   | High     | Medium | Open   | Trends: fixed Y-axis / legend on horizontal scroll           |
| O-61 | P4-C   | Medium   | Medium | Open   | Trends: floating toolbar like Insights (incl. mobile)        |
| O-62 | P4-A   | Critical | Medium | Open   | Insights: Symptom calendar/progression viewport overflow fix |

O-50 (Insights responsive axis) is satisfied as part of P4-A (O-62).

---

## Sprint plan

```mermaid
flowchart LR
  P4A["P4-A O-62/O-50"] --> P4B["P4-B O-59"]
  P4B --> P4C["P4-C O-60/O-61"]
  P4C --> P4D["P4-D O-57/O-58"]
```

### Sprint P4-A — Insights overflow (O-50, O-62)

**Branch:** `cursor/sprint-p4a-insights-overflow-e965`

- SSR-safe `compareDailyAxisLayoutFromRoot(16)` initial state
- Harmonized scroll containers in `SymptomAnalyticsSection`
- Calendar scroll affordance on mobile
- E2E: no page-level horizontal overflow at 390px

### Sprint P4-B — Heatmap density (O-59) ✅

**Branch:** `cursor/bugfix-587-588-590-d93d` (#590)

- `heatmapPruning.ts` utility + `pruneHeatmapRowsByBuckets` for Compare zoom
- Integration in `ComparisonHeatmap`, co-occurrence matrices
- `pruneSparseAxes=true` on all viewports (desktop + mobile)

### Sprint P4-C — Trends scroll & sticky (O-60, O-61)

**Branch:** `cursor/sprint-p4c-trends-mobile-chrome-e965`

- Split chart layout: fixed gutter + scrollable plot
- `TrendsAnalysisToolbar.svelte` (range + tabs + filters)
- Re-enable sticky toolbar on mobile

### Sprint P4-D — Home (O-57, O-58)

**Branch:** `cursor/sprint-p4d-home-weekday-cta-e965`

- Hide Zone-1 CTA when `!todayEntry` (Zone 3 remains)
- `HomeWeekdayOverview.svelte` with 7-day findings strip

---

## GitHub issue

Track as: `[UX] Mobile: Home-CTA, Wochentags-Übersicht, Heatmap-Dichte, Trends-Sticky, Insights-Overflow`

See Phase 4 issue body in repository issues (labels: `bug`, `ux`, `mobile`).

---

## Phase 4 follow-up (O-63 – O-64)

Follow-up to mobile UX review after P4 merge candidate [#339](https://github.com/Sturmi77/correlcore/pull/339).

| ID   | Sprint | Impact | Effort | Status | Title                                                         |
| ---- | ------ | ------ | ------ | ------ | ------------------------------------------------------------- |
| O-63 | P4-D   | High   | Low    | Open   | Home: encode work-context bars by mood, not entry frequency   |
| O-64 | P4-C   | High   | Medium | Open   | Trends mobile: compact quick filters + compare settings sheet |

### O-63 — Home work-context pattern

- `homeWorkContextSummary.ts`: weighted mood average, sort by deviation, bar width from mood (1–5)
- `HomeDailyBrief.svelte`: high/low bar highlights; copy `{mood} · {count} Tage`

### O-64 — Trends mobile control density

- Sticky toolbar: range + tabs only (revises O-61 filter row on mobile; restores O-29 spirit)
- `TrendsCompareQuickFilters.svelte`: metric chips + category + **Anpassen**
- `TrendsCompareSettingsSheet.svelte`: smoothing, metrics, category, layers, mode, sort
- `TrendsComparePanel.svelte`: `compactChrome` hides header/controls on mobile

**Branch:** `cursor/home-trends-followup-e965`
