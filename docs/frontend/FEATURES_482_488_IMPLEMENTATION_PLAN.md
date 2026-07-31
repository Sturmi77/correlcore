# Implementation Plan — #482 (Strip bucket aggregation) & #488 (Lag visualization)

> Status: approved. Policy for #482 = **Option A** (encode the bucket mean, parity
> with Lines). #488 recommendation approved: Phase 1 + Phase 1b (lag profile),
> Phase 2 heatmap deferred. Grounded on code as of `main` @ this branch point.

---

## Feature #482 — Trends Compare: strip-mode bucket aggregation

### Current state (verified)

- **Strip gate active.** `TrendsComparePanel.svelte` forces
  `effectiveZoomStage = mode === 'strips' ? 0 : zoomStage` (~L214). Switching to
  Strips resets zoom in `setMode` (~L125–133) and raises `stripGateNotice`. Zoom
  buttons are disabled in strip mode (`canZoomOut/In = mode === 'lines'`, ~L224).
- **Strip renders one cell per day.** `UnifiedStripChart.svelte` `buildRow`
  (~L115–135) walks `axisDates` + a `byDate` lookup and encodes the display value
  divergently via `StripCellMapper({ midpoint: 3, range: 4 })`. This is a
  fixed-midpoint divergent encoding on the 1–5 scale, **not** a statistical
  Z-score.
- **Lines already consumes buckets.** `buildAxisBuckets` + `meanBucketMetric`
  (mean of logged days, empty → `null`) in `compareAxisZoom.ts`.
  `findBucketForDate` exists for cursor sync.

### Decision — aggregation policy = Option A

Collapse N days into one bucket cell by **encoding the bucket mean**:
`meanBucketMetric(displayValue)` → `StripCellMapper.encode`. This is the same
truth as Lines (`mean-of-logged-days`), so there is no dual truth versus the
heatmap columns, and it reuses the existing util.

Rejected: mean of per-day encodings (diverges from Lines, harder to explain).

### Steps

1. `UnifiedStripChart`: add `buckets?: AxisBucket[]` prop. When present
   (stage > 0), render one cell per bucket. Per bucket + metric, compute
   `meanBucketMetric(date => displayTimeseriesValue(key, raw))` then
   `mapper.encode`. Cell x/width from the bucket layout. Empty-day handling:
   `bucket.partial` / low `presentDays` → reduced opacity (or hatch).
2. `TrendsComparePanel`: drop the strip gate — `effectiveZoomStage = zoomStage`
   for strips too; pass `axisBuckets` + `bucketAxisLayout` into
   `UnifiedStripChart`; enable zoom controls in strip mode; remove
   `stripGateNotice` + the `strips_disabled` i18n usage.
3. Cursor sync: set the `timelineCursor` axis to bucket starts (as Lines does);
   map `nearestDateForX` to the bucket start.
4. Tests: strip cell count = `buckets.length`, aggregation value, partial
   styling; panel keeps zoom when switching to strips; cursor sync across
   buckets.

**Effort:** M (frontend only, primitives ready). **Dependency:** #472 device-QA
sign-off (per issue).

---

## Feature #488 — Lag correlation visualization

### Current state (verified)

- **Backend computes the full lag matrix but keeps one value.**
  `run_lag_analysis` (`multivariate_analytics.py`) correlates every lag
  `1..MAX_LAG_DAYS (=7)` per pair, but returns only the best `LagFinding`
  (single `lag_days`, single `correlation`). No `r[lag]` series in the payload.
- **Payload** (`insight_engine.py`, `method="lag"`): target/feature/`lag_days`/
  correlation — no `lag_profile`.
- **Event windows ignore lag.** `get_insight_event_windows`
  (`insight_service.py`) aligns onsets on the **subject (= target/outcome)**,
  not the feature, and does not use `lag_days`. `InsightEventWindow` schema =
  `onset` + `label` only.
- **Sheet.** `EventAlignedSmallMultiplesSheet.svelte` aligns each window at
  t=0=onset over −7..+7; no +lag marker.
- **InsightCard** shows only the `(+N days)` title suffix.

### Phase 1 (issue points 1–2)

1. Event windows lag-aware (backend): for `payload.method == "lag"`, derive
   onsets from the **feature** (`payload.feature`, tag/symptom) instead of the
   subject; include `lag_days` in the response. Resolve the feature slug like
   `_resolve_tag_slug`/`_resolve_symptom_slug`. Edge case: a metric feature has
   no presence dates → Phase 1 handles tag/symptom features only, otherwise
   annotate-only fallback.
2. Schema: optional `lag_days` on `InsightEventWindowsResponse` + web type
   mirror in `insights.ts`.
3. Sheet: `lagOffset` prop → highlighted column at t=+lag_days (marker +
   annotation). Onset stays t=0 (feature); highlight = expected outcome.
4. InsightCard: always show a lag annotation; the mini lag-profile bars
   (days 1–7) render only if the payload carries `lag_profile` (see 1b).

### Phase 1b (enables the profile bars, backend)

5. Extend `LagFinding` + payload with `profile: r[1..7]` for the winning pair,
   grouped from the `raw` correlations already gathered. Emit `lag_profile` in
   the payload. Gates unchanged (`MIN_ML_ENTRIES=90`, FDR, non-causal copy). No
   new raw data — aggregated statistics only (privacy-safe per issue).

### Phase 2 (follow-up, not a blocker)

6. Lag-correlation heatmap (pair × lag) per ADR-0035 — separate issue/PR.

### Tests

`test_multivariate_analytics` (profile series, grouping), `insight_service`
event-windows lag branch, web: InsightCard profile + Sheet lag marker.

**Effort:** L overall; Phase 1 without profile bars ≈ M.

---

## Recommended sequencing

1. **#482** first (smaller, frontend-only, primitives ready) — this plan.
2. **#488** in two PRs: (A) event-windows lag-aware + Sheet marker + Card
   annotation; (B) backend `lag_profile` + Card bars. Heatmap (Phase 2)
   separate.
