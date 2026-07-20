# Trends Compare Axis Zoom — Implementation Plan

**Status:** Implemented (CAZ-1…3; Slice F not required pending device row 8)  
**Date:** 2026-07-20  
**Product/concept:** [`COMPARE_AXIS_ZOOM_PLAN.md`](COMPARE_AXIS_ZOOM_PLAN.md)  
**Sprint plan:** [`COMPARE_AXIS_ZOOM_SPRINT_PLAN.md`](COMPARE_AXIS_ZOOM_SPRINT_PLAN.md)  
**QA:** [`../quality/COMPARE_AXIS_ZOOM_CAZ3_QA.md`](../quality/COMPARE_AXIS_ZOOM_CAZ3_QA.md)  
**Issue:** [#472](https://github.com/Sturmi77/correlcore/issues/472) · Strip Z follow-up [#482](https://github.com/Sturmi77/correlcore/issues/482)  
**Stack:** SvelteKit web only (same UI in PWA / Capacitor WebView) — no backend change in v1

Engineering execution for slices A–E is in the CAZ PRs. **Sprint packaging**
(A+B+C → D → E/F) lives in the sprint plan. Strip Z-score bucket policy is
deferred to #482.

---

## 0. Preconditions (WP0) — done

- [x] Concept plan §4 confirmed 2026-07-20:
  - Default stage **7**
  - Range chips in Compare **hidden**; axis window **365d**
  - Stages **`1/3/7/14/28`**
  - Tap zoom-in **one stage finer**
- [x] Docs plans merged (#473, #477)
- Branch naming for implementation: `cursor/compare-axis-zoom-s1-d121` (then
  `s2` / `s3`), or `cursor/compare-axis-zoom-<slice>-d121`.

---

## 1. Architecture (target)

```text
trends/+page.svelte
  └─ load Compare window = 365d (timeseries year + heatmaps)
       └─ TrendsComparePanel
            ├─ zoomStage (persisted) + +/- chrome
            ├─ dailyAxisDates (ISO, full window)
            ├─ axisBuckets = buildAxisBuckets(dailyAxisDates, stage)
            ├─ axisLayout (bucket column width ≥ tap target)
            ├─ MetricTimeseries | UnifiedStripChart  ← same buckets
            └─ ComparisonHeatmap                     ← same buckets
                 timelineCursor.axisKeys = bucket starts (or dates at stage 0)
```

**Ownership:** `TrendsComparePanel` owns zoom stage, bucket list, scroller, and
cursor axis publication. Children remain presentational over the display axis.

**Invariant:** Chart and heatmap never build independent axes.

---

## 2. Suggested PR slices

Slices are the engineering breakdown. **Shipping cadence** groups them into
sprints (see sprint plan): **Sprint 1 = A+B+C**, **Sprint 2 = D**,
**Sprint 3 = E (+F if needed)** — one primary PR per sprint.

| Slice | Name                               | Depends          | Delivers                           | Sprint       |
| ----- | ---------------------------------- | ---------------- | ---------------------------------- | ------------ |
| **A** | Pure zoom math + persistence       | WP0              | Utils + settings + unit tests      | 1            |
| **B** | Panel chrome + 365d Compare load   | A                | `+/-`, status, year window wiring  | 1            |
| **C** | Heatmap + Lines on buckets         | A, B             | Shared render, cursor, scroll sync | 1            |
| **D** | Tap zoom-in + tooltips/legend i18n | C                | Interaction + interpretability     | 2            |
| **E** | Strip/marker gate + Capacitor QA   | D                | No dual-truth; device checklist    | 3            |
| **F** | Perf follow-up                     | E only if needed | Virtualisation / stage soft-cap    | 3 (optional) |

---

## 3. Slice A — Pure math & persistence

### 3.1 New module

Create `apps/web/src/lib/utils/compareAxisZoom.ts`:

```ts
export const COMPARE_ZOOM_STAGES = [1, 3, 7, 14, 28] as const;
export type CompareZoomStageIndex = 0 | 1 | 2 | 3 | 4;

export type AxisBucket = {
  id: string; // `${start}_${end}`
  start: string; // ISO inclusive
  end: string; // ISO inclusive
  dayCount: number; // stage size (e.g. 7)
  presentDays: number; // dates.length
  partial: boolean;
  dates: string[]; // ISO days in bucket (chronological)
};

export function stageDays(stage: CompareZoomStageIndex): number;
export function clampZoomStage(stage: number): CompareZoomStageIndex;
export function buildAxisBuckets(
  axisDatesOldestToNewest: readonly string[],
  stage: CompareZoomStageIndex
): AxisBucket[];
/** Heatmap: sum of daily counts over bucket.dates */
export function sumBucketCounts(valueForDate: (date: string) => number, bucket: AxisBucket): number;
/** Metrics: mean of non-null daily values for days with data */
export function meanBucketMetric(
  valueForDate: (date: string) => number | null | undefined,
  bucket: AxisBucket
): number | null;
```

**Bucket algorithm (required):**

1. Input `axisDates` oldest → newest (as `buildIsoDateRange` today).
2. Walk **from the end** (newest) backward in chunks of `stageDays`.
3. Each chunk becomes one bucket; remaining older days form the leftmost
   (possibly partial) bucket.
4. Emit buckets oldest → newest so index 0 is left, last is right (scroll latest).
5. `partial = presentDays < dayCount` (also true if clipped by window edges).

### 3.2 Persistence

Extend `apps/web/src/lib/utils/comparePanelSettings.ts`:

- `COMPARE_ZOOM_KEY = 'cc_trend_compare_zoom'`
- `readCompareZoomStage(): CompareZoomStageIndex` — default **`2`** (7 days)
- `writeCompareZoomStage(stage)`
- `isCompareZoomStage(value)`

### 3.3 Tests (Slice A)

`apps/web/src/lib/utils/compareAxisZoom.test.ts`:

| Case                         | Expect                                 |
| ---------------------------- | -------------------------------------- |
| 28 consecutive days, stage 7 | 4 full buckets                         |
| 30 days, stage 7             | leftmost partial (2d) + 4×7            |
| stage 0                      | N buckets of 1 day each                |
| newest-right                 | last bucket `end` === last axis date   |
| sum over sparse zeros        | correct sum                            |
| mean skips null/empty days   | mean of present only; all-empty → null |
| clamp                        | `-1→0`, `9→4`                          |

`comparePanelSettings` tests for zoom read/write/default.

### 3.4 Exit A

- Pure functions only; no UI.
- `pnpm --filter @correlcore/web test` covers new unit files.

---

## 4. Slice B — Panel chrome + year data window

### 4.1 `TrendsComparePanel.svelte`

Add:

- State `zoomStage = readCompareZoomStage()`
- Derived `axisBuckets = buildAxisBuckets(axisDates, zoomStage)`
- Zoom control group above `.compare__axis-scroller` (mirror
  `TagCooccurrenceHeatmap` density chrome):
  - `data-testid="trends-compare-zoom"`
  - decrease (`−` / coarser), increase (`+` / finer)
  - status text via i18n (`{days}` / cell)
  - disable at stage 4 / 0 respectively
- On stage change: `writeCompareZoomStage`, clear or remap cursor, include
  stage in scroll `axisKey` so layout refresh stays sane (still scroll-to-latest
  on window change; on zoom prefer **preserve focus bucket** if cursor set —
  implement preserve in Slice D if too heavy here; Slice B may scroll-latest)

Props: optional `bind:zoomStage` only if mobile settings sheet needs it later;
v1 can keep stage internal to the panel.

### 4.2 `trends/+page.svelte`

For Compare data path:

- Always request **year / 365d** for timeseries + tag/symptom/work-context
  heatmaps used by Compare (concept D2).
- Global range control: **hide or disable while Compare tab active**, or keep
  for other tabs (Habits/Health) but do not shrink Compare axis.
  Preferred: when `activeTab === 'compare'` (or equivalent), force
  `dateWindow(365)` + `fetchTimeseries('year')` regardless of chip UI.
- Update `page.test.ts`: Compare load asserts `fetchTimeseries('year')` and
  heatmap window length 365.

### 4.3 i18n (minimal for chrome)

`en.json` / `de.json` under `trends.compare.zoom.*`:

- `label`, `decrease_aria`, `increase_aria`, `status` (`{days}`),
  `encoding_sum`, `encoding_mean` (encoding strings can land in Slice D)

### 4.4 Layout width

When `stage > 0`, use bucket column width ≥ coarse-pointer tap target
(reuse `--tap-target` / existing heatmap cell min). Prefer slightly **wider**
columns when fewer buckets (readability), not tinier.

Helper options:

- Keep `DailyAxisLayout.dayWidth` meaning “column width”, feed bucket count
  into `dailyPlotContentWidth(buckets.length, layout)`.

### 4.5 Exit B

- `+/-` visible; stage persists across reload.
- Compare always fed 365d data.
- Heatmap/chart still daily until Slice C (acceptable intermediate: chrome
  only changes stage state, or already pass buckets if C is same branch —
  prefer **same branch A→B→C** if one implementer; else B may show controls
  no-op on render until C).

**Recommendation:** Implement A+B+C on one feature branch if capacity allows;
split PRs only if review size demands it. If split, B must not claim
bird’s-eye done until C merges.

---

## 5. Slice C — Shared bucket render (Lines + Heatmap)

### 5.1 Contract change

Prefer additive props to avoid a big bang:

| Component        | Today                                      | After                                                                                                            |
| ---------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Panel → children | `dates={axisDates}`                        | `dates={axisDates}` kept for prune/raw + **`buckets={axisBuckets}`**                                             |
| Heatmap          | one cell per date                          | if `buckets.length`, one cell per bucket; value = sum                                                            |
| MetricTimeseries | `buildDailyAxisLinePoints(..., axisDates)` | if buckets: build points with `label = bucket.start` (or `id`), `x` by bucket index, `y` from `meanBucketMetric` |
| Cursor           | `setAxis(axisDates)`                       | `setAxis(buckets.map(b => b.start))` at stage>0; daily at stage 0                                                |

**Minimal cursor extension (v1):** keep `timelineCursor.date` as the **display
axis key** = `bucket.start` (stage 0 ⇒ that day). Keyboard `move(±1)` advances
one column. Tooltip/overlay resolves start→bucket for range label.

Optional later: `{ bucketStart, bucketEnd }` fields — not required if overlay
can look up bucket by start.

### 5.2 `ComparisonHeatmap.svelte`

- Accept `buckets?: AxisBucket[]` (empty/undefined ⇒ legacy daily `dates`).
- `visibleColumns = buckets ?? dates-as-degenerate-buckets`.
- Cell click:
  - stage 0 / 1-day bucket → `selectDate` with that date (existing).
  - multi-day → dispatch new event `zoomInBucket: { bucket }` **or** handle via
    callback prop from Panel (Slice D). For Slice C, multi-day tap may no-op or
    still zoom if D is same PR.
- Colour: `heatmapLevel(sum, maxSumAcrossVisible)`.
- Partial: CSS modifier `compare-heatmap__cell--partial`.
- **Do not** prune columns by sparsity when zoomed (keep alignment). Row prune
  (`pruneSparseAxes`) stays row-only.

### 5.3 `MetricTimeseries.svelte`

- When `buckets` provided and length > 0, align series to buckets.
- Gaps: `null` mean ⇒ break line / omit point (match current empty-day behaviour).
- Pointer → nearest bucket start; `selectDate` on point click:
  - 1-day: existing
  - multi-day: defer to Panel zoom-in (Slice D)

### 5.4 Markers / notes

Map marker/note dates into the bucket that **contains** the date; draw once per
bucket (dedupe). If ambiguous, first match wins.

### 5.5 Tests (Slice C)

- `ComparisonHeatmap.test.ts`: given 14 days stage 7 → 2 cells/row; sums match.
- `TrendsComparePanel.test.ts`: changing zoom changes column count in chart +
  heatmap together; scroll container still present.
- `charts.test.ts` / zoom util: width helpers with bucket count.
- Cursor: arrow key moves by bucket start keys.

### 5.6 Exit C

- Zoom coarsens **both** layers identically.
- Stage 0 visually matches pre-feature daily Compare (parity test).
- Strip mode: **gate** — if `mode === 'strips' && zoomStage > 0`, either force
  stage 0 or disable strip toggle (full Strip bucket work in Slice E).

---

## 6. Slice D — Interaction + interpretability

### 6.1 Tap zoom-in

Panel handler:

```ts
function zoomInBucket(bucket: AxisBucket): void {
  if (zoomStage === 0) return; // day handled via selectDate
  const next = clampZoomStage(zoomStage - 1);
  zoomStage = next;
  writeCompareZoomStage(next);
  // after tick: scroll so bucket.start..bucket.end visible; set cursor to
  // containing column at new stage
}
```

- Heatmap / chart multi-day activation → `zoomInBucket`.
- Day column → existing `selectDate` → page opens `EntryHistorySheet`.

### 6.2 Affordance + legend

- Near `+/-`: short dual-encoding hint (sum vs mean).
- Tooltip / cursor card fields:
  - date range (`start`–`end`)
  - metric means
  - heatmap sums for hovered row or summary
  - coverage `entryDays/presentDays` and partial `"k of N days"`
- **No** ISO week (“KW”) labels.

### 6.3 i18n complete

All user-visible strings DE/EN under `trends.compare.zoom.*`.

### 6.4 Tests

- Tap multi-day cell decreases stage and keeps interval on screen (scroll mock /
  spy).
- Tap day cell fires `selectDate` once, does not change stage.
- Tooltip/coverage unit coverage where extracted to helpers.

### 6.5 Exit D

- Concept D5/D6 satisfied; R2/R3/R6/R7 mitigations visible in UI.

---

## 7. Slice E — Strip gate, markers polish, Capacitor QA

### 7.1 Strip mode

Until strip Z-score aggregation is explicitly defined:

- **Option 1 (preferred):** selecting Strips while `zoomStage > 0` resets to
  stage 0 (with status text).
- **Option 2:** disable Strips chip when `zoomStage > 0` with explanation.

Document follow-up issue for: mean of daily Z vs Z of bucket mean.

### 7.2 Capacitor / mobile checklist (manual)

Run against WebView build or `pnpm dev` in device browser:

| Check                                                   | Pass? |
| ------------------------------------------------------- | ----- |
| `+/-` reachable, ≥44px targets                          |       |
| Horizontal scroll does not trigger accidental zoom      |       |
| Tap zoom-in works with touch                            |       |
| Stage 0 tap opens history sheet                         |       |
| Partial bucket readable                                 |       |
| Year data + stage 7 default after clear storage         |       |
| Persist stage after app background/resume               |       |
| Stage 0 scroll performance acceptable with typical rows |       |

Attach notes on #472. If stage 0 janks → open Slice F.

### 7.3 Exit E

- No dual-truth strip/zoom combo.
- QA notes filed; v1 shippable without Pinch.

---

## 8. Slice F — Perf (conditional)

Only if Slice E fails stage-0 performance:

1. Measure: columns × rows DOM nodes in Compare.
2. Options (pick smallest fix):
   - Virtualise horizontal columns outside viewport ± buffer.
   - Soft-cap: on coarse pointer + low memory, default/min stage ≥ 1.
   - Reduce per-cell DOM (CSS grid backgrounds vs button-per-cell) while keeping
     a11y hit targets.

Exit: stage 0 usable on target Android profile.

---

## 9. File checklist (v1)

| File                                                                   | Slice | Action                                                                                  |
| ---------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------- |
| `apps/web/src/lib/utils/compareAxisZoom.ts`                            | A     | **Create**                                                                              |
| `apps/web/src/lib/utils/compareAxisZoom.test.ts`                       | A     | **Create**                                                                              |
| `apps/web/src/lib/utils/comparePanelSettings.ts`                       | A     | Extend zoom persist                                                                     |
| `apps/web/src/lib/utils/comparePanelSettings.test.ts`                  | A     | Extend (create if missing)                                                              |
| `apps/web/src/lib/components/trends/TrendsComparePanel.svelte`         | B–D   | Zoom state, chrome, buckets, handlers                                                   |
| `apps/web/src/lib/components/trends/TrendsComparePanel.test.ts`        | B–D   | Zoom + sync tests                                                                       |
| `apps/web/src/lib/components/trends/ComparisonHeatmap.svelte`          | C–D   | Bucket cells, sum, partial, tap                                                         |
| `apps/web/src/lib/components/trends/ComparisonHeatmap.test.ts`         | C–D   | Aggregated columns                                                                      |
| `apps/web/src/lib/components/trends/MetricTimeseries.svelte`           | C–D   | Bucket series + cursor                                                                  |
| `apps/web/src/lib/components/trends/UnifiedStripChart.svelte`          | E     | Gate or bucket later                                                                    |
| `apps/web/src/lib/stores/timelineCursor.ts`                            | C     | Axis keys = bucket starts (doc update)                                                  |
| `apps/web/src/lib/utils/charts.ts`                                     | C     | Optional helpers if needed                                                              |
| `apps/web/src/routes/trends/+page.svelte`                              | B     | 365d Compare load / range decoupling                                                    |
| `apps/web/src/routes/trends/page.test.ts`                              | B     | Year fetch assertions                                                                   |
| `apps/web/src/lib/i18n/locales/en.json`                                | B/D   | Zoom strings                                                                            |
| `apps/web/src/lib/i18n/locales/de.json`                                | B/D   | Zoom strings                                                                            |
| `apps/web/src/lib/components/trends/TrendsCompareSettingsSheet.svelte` | B?    | Only if zoom control duplicated for mobile sheet (O-64) — prefer single chrome in panel |

**Out of touch:** Habit `TagHeatmap`, symptom calendar, backend stats endpoints,
LayerChart adapter.

---

## 10. Definition of Done (feature)

Matches concept plan acceptance + engineering:

1. [ ] Default stage 7 on first visit (empty localStorage).
2. [ ] Stages `1/3/7/14/28` via `+/-`; status always visible.
3. [ ] Shared scroller: identical column count/positions for Lines + Heatmap.
4. [ ] Heatmap = sum; metrics = mean of days with entries; coverage in UI.
5. [ ] Partial buckets shown, not upscaled.
6. [ ] Multi-day tap → zoom-in; day tap → EntryHistorySheet.
7. [ ] Compare data window 365d; range does not fight zoom.
8. [ ] Strip/zoom dual-truth impossible.
9. [ ] Unit + component tests green; `pnpm --filter @correlcore/web test` /
       targeted files; `pnpm lint` / typecheck on touched packages.
10. [ ] Capacitor/mobile checklist completed on #472.
11. [ ] Concept + this implementation plan marked **Implemented** with PR links.

---

## 11. Implementation order (single-developer path)

Recommended one-branch sequence if not splitting reviews:

1. Slice A utils + tests
2. Slice B persistence + chrome + year load
3. Slice C heatmap + lines bucket wiring + cursor
4. Slice D tap + tooltips/legend
5. Slice E strip gate + device QA
6. Slice F only if needed

Commit before each testable milestone; open draft PR early against #472.

---

## 12. Explicit non-goals (do not implement in these slices)

- Pinch gestures
- Backend `granularity=` APIs
- ISO calendar-week alignment
- Habit / symptom-calendar heatmaps
- React parallel GUI
- Coverage heat overlay (v1.1 candidate)

---

## 13. Traceability

| Concept WP | Implementation slice        |
| ---------- | --------------------------- |
| WP0        | §0 Preconditions            |
| WP1        | Slice B                     |
| WP2        | Slice A (+ colour max in C) |
| WP3        | Slice C                     |
| WP4        | Slice D                     |
| WP5        | Slice D                     |
| WP6        | Slice E                     |
| WP7        | Slice E                     |
| WP8        | Slice F                     |
