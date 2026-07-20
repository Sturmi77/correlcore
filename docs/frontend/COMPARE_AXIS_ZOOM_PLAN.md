# Trends Compare — Shared Axis Zoom (Bird’s-Eye) Plan

**Status:** Proposed (product decisions locked below; implementation not started)  
**Date:** 2026-07-20  
**GitHub:** [#472](https://github.com/Sturmi77/correlcore/issues/472) · Plan PR [#473](https://github.com/Sturmi77/correlcore/pull/473)  
**Area:** Frontend / Trends Compare (`MetricTimeseries` | `UnifiedStripChart` + `ComparisonHeatmap`)  
**Related:** [ADR-0035](../adr/0035-temporal-correspondence-pattern.md), [`SYMPTOM_VISUALIZATION.md`](SYMPTOM_VISUALIZATION.md), O-17 (heatmap → `EntryHistorySheet`), O-59 (`heatmapPruning.ts`), Co-Occurrence density `+/-`

---

## 1. Problem

The Compare view already shares one horizontal scroller and daily axis between
Mood/Energy/Stress and the Comparison Heatmap. At year scale that axis is
~365 day columns: patterns that span weeks are hard to see; changing the global
range chips mostly reloads a shorter window and does little for “bird’s-eye”
pattern reading.

Users need a **display zoom** that coarsens the shared axis (multiple days per
column) while chart and heatmap stay locked together — including on PWA /
Capacitor.

---

## 2. Goals

| Goal             | Meaning                                                               |
| ---------------- | --------------------------------------------------------------------- |
| Intuitiveness    | One control (`+/-`), visible zoom status, predictable tap             |
| Expressiveness   | Week/fortnight/month columns make multi-day episodes readable         |
| Interpretability | Clear dual encoding (heatmap sum vs metric mean) + coverage honesty   |
| Platform parity  | Same Web UI works in Capacitor WebView (no Pinch required in v1)      |
| Sync integrity   | Chart + heatmap always share identical bucket columns, scroll, cursor |

Non-goals for v1 are listed in §11.

---

## 3. Locked product decisions

| #   | Decision                                                                                                                                                 |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Scope = Trends **Compare unit** only (timeline + `ComparisonHeatmap`).                                                                                   |
| D2  | Zoom changes **display granularity only**; loaded horizon stays **365 days**.                                                                            |
| D3  | Heatmap bucket value = **sum of daily occurrence counts** (tags, work context; symptoms: sum of daily counts — intensity separate in tooltip if useful). |
| D4  | Mood / Energy / Stress bucket value = **mean of days that have an entry** (do not average in empty days).                                                |
| D5  | Tap on a **multi-day bucket** = **zoom in** (drill toward finer granularity), not open entry history.                                                    |
| D6  | Tap on a **day** column (zoom stage 0) = existing behaviour (`EntryHistorySheet` / `selectDate`).                                                        |
| D7  | v1 interaction = **`+/-` buttons** (same metaphor as Co-Occurrence density), not Pinch.                                                                  |
| D8  | Capacitor must be a first-class target (touch targets, no scroll/gesture conflict).                                                                      |

---

## 4. Recommended defaults (product)

These close the remaining open points; change only with explicit product override.

| Topic                  | Recommendation                                                                                           | Rationale                                                               |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Zoom stages            | `1 → 3 → 7 → 14 → 28` days/column                                                                        | Enough bird’s-eye steps without continuous zoom complexity              |
| Default stage          | **7** when Compare loads the 365d window                                                                 | Year-at-a-glance is the primary new value                               |
| Range chips in Compare | **Fix data window to year (365d)** for the shared axis; hide or disable range as axis control in Compare | Avoid two competing controls; other Trends panels may keep range later  |
| Persist                | `localStorage` key `cc_trend_compare_zoom` (stage index 0–4)                                             | Consistent with `cc_trend_compare_mode` / sort                          |
| Bucket alignment       | Build buckets **from newest day backward**                                                               | Matches newest-right scroll; “today” bucket is the natural partial edge |
| Partial edge buckets   | **Show**, mark visually + tooltip `"k of N days"`; aggregate only over days present — **never upscale**  | Honesty > fake completeness                                             |
| Zoom-in depth          | One stage finer per tap, then scroll/focus that interval into view                                       | Predictable; avoids jumping past useful mid levels                      |
| Status chrome          | Always show e.g. “7 Tage / Zelle” next to `+/-`                                                          | Prevents persisted-zoom surprise                                        |

---

## 5. Dual encoding (interpretability contract)

On one shared time axis, two different aggregations are intentional:

| Layer                                              | Encoding                     | User-facing label (i18n)                 |
| -------------------------------------------------- | ---------------------------- | ---------------------------------------- |
| Comparison Heatmap cells                           | Sum of occurrences in bucket | e.g. `trends.compare.zoom.encoding_sum`  |
| Mood / Energy / Stress line (and later strip mean) | Mean of days **with** entry  | e.g. `trends.compare.zoom.encoding_mean` |

**Required UI copy (v1):**

1. Short legend or control hint near `+/-` stating both encodings.
2. Cursor/tooltip per bucket: interval dates, metric means, heatmap sums, and
   **coverage** `entry_days / bucket_days` (and for partial buckets `present_days / stage_days`).

Without this, users will read a dark heatmap week as “bad/high mood week”.

---

## 6. Risks and mitigations (integrated)

| ID  | Risk                                     | Negative consequence                          | Mitigation (in scope)                                                                                                                | WP       |
| --- | ---------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| R1  | Sum scales with bucket length            | Weeks look “louder”; short peaks vanish       | Colour levels relative to **max visible bucket sum**; legend “Summe”; tooltip raw sum + active days                                  | WP2, WP5 |
| R2  | Sum (heatmap) vs mean (metrics) confused | False correspondence                          | Dual-encoding legend + tooltip fields                                                                                                | WP5      |
| R3  | Mean ignores empty days                  | Sparse week with one good day looks “fine”    | Always show coverage in tooltip; optional faint coverage cue later (v1.1)                                                            | WP5      |
| R4  | 365 × rows DOM at stage 0                | Jank on Capacitor when zooming back to days   | Measure on device; if needed virtualise columns or cap mounted day-columns (follow-up WP8)                                           | WP7, WP8 |
| R5  | Removing range focus window              | Power users lose “only this week” mental mode | Zoom-in + scroll-into-view approximates focus; document; revisit dedicated focus window only if feedback demands                     | WP1, WP6 |
| R6  | Tap no longer opens sheet on buckets     | Interaction regression vs O-17 habit          | Stage 0 keeps sheet; affordance text on multi-day (“Tippen zum Vergrößern”); optional long-press → sheet later                       | WP4, WP5 |
| R7  | Persisted zoom surprise                  | “UI looks broken” after reload                | Persistent visible status; first-run may default 7 without punishing experts who chose 1                                             | WP3, WP5 |
| R8  | Backward buckets ≠ calendar ISO weeks    | Users compare to KW labels and mismatch       | Label intervals as date ranges, not “KW”; avoid calendar-week claims in v1                                                           | WP2, WP5 |
| R9  | Cursor/`timelineCursor` still date-keyed | Desync, a11y says wrong day                   | Extend cursor model to `{ bucketStart, bucketEnd, stage, source }` (date retained for stage 0)                                       | WP3      |
| R10 | Strip mode / markers lag lines           | Two truths in one panel                       | **v1 ships Lines + heatmap zoom first**; Strips and marker alignment gated in WP6; disable strip toggle or force stage 0 until ready | WP6      |

---

## 7. Technical design sketch

### 7.1 Shared axis contract

Replace the Compare panel’s exclusive reliance on flat `axisDates: string[]` for
_rendering_ with:

```ts
type CompareZoomStage = 0 | 1 | 2 | 3 | 4; // → 1 | 3 | 7 | 14 | 28 days

type AxisBucket = {
  id: string; // e.g. `${start}_${end}`
  start: string; // ISO date inclusive
  end: string; // ISO date inclusive
  dayCount: number; // stage size (e.g. 7)
  presentDays: number; // days inside loaded window
  partial: boolean; // presentDays < dayCount OR clipped by window
  dates: string[]; // ISO days actually in this bucket
};
```

- Source daily series remain unchanged (client expands sparse heatmap + daily
  timeseries as today).
- `buildAxisBuckets(axisDates, stage)` is pure and unit-tested.
- `TrendsComparePanel` owns `zoomStage`, passes `buckets` + layout into chart and
  heatmap.
- One scroller; column width from shared `axisLayout` (reuse/extend
  `DailyAxisLayout` → bucket width ≥ tap target on coarse pointers).

### 7.2 Aggregation helpers

| Input                               | Output                                                        |
| ----------------------------------- | ------------------------------------------------------------- |
| Tag/work-context daily counts       | `sum(count)` over `bucket.dates`                              |
| Symptom daily                       | `sum(count)`; expose `max(max_intensity)` in tooltip          |
| Timeseries daily mood/energy/stress | mean of non-null daily avgs among days with `entry_count > 0` |
| Empty metric bucket                 | gap (no point), same as missing days today                    |

Colour: `heatmapLevel(bucketSum, maxVisibleBucketSum)` — existing 0–4 levels.

### 7.3 Interaction

| Control                | Behaviour                                                                                                               |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `−`                    | `stage = min(4, stage + 1)` (coarser)                                                                                   |
| `+`                    | `stage = max(0, stage - 1)` (finer)                                                                                     |
| Tap bucket `stage > 0` | `stage -= 1` (or map to finest that still contains interval); scroll so bucket span is visible; set cursor to that span |
| Tap day `stage === 0`  | `dispatch('selectDate')` → Entry history (unchanged)                                                                    |
| Hover/focus            | Update shared cursor store with bucket span                                                                             |

Persist stage on change. No Pinch in v1 (avoids conflict with horizontal scroll
in Capacitor).

### 7.4 Range / data loading

- Compare axis data window: **always 365 days** for this feature path (align
  heatmap `start_date`/`end_date` + timeseries year).
- Global Trends range control: either hidden in Compare tab or decoupled so it
  does not shrink the shared axis while zoom exists (implementation choice in
  WP1 — prefer hide/disable for Compare to reduce dual-control confusion).

### 7.5 Files likely touched

- `apps/web/src/lib/components/trends/TrendsComparePanel.svelte`
- `apps/web/src/lib/components/trends/ComparisonHeatmap.svelte`
- `apps/web/src/lib/components/trends/MetricTimeseries.svelte`
- `apps/web/src/lib/components/trends/UnifiedStripChart.svelte` (WP6)
- `apps/web/src/lib/stores/timelineCursor.ts`
- `apps/web/src/lib/utils/charts.ts` (+ new `compareAxisZoom.ts` or similar)
- `apps/web/src/routes/trends/+page.svelte` (range vs zoom wiring)
- i18n `de.json` / `en.json`
- Tests: unit for buckets/aggregation; component tests for `+/-` and tap zoom-in;
  Capacitor/manual checklist WP7

No backend API change required for v1 (client-only aggregation on daily
payloads).

---

## 8. Work packages

### WP0 — Spec freeze & issue tracking

- [x] Decisions D1–D8 documented
- [x] GitHub issue opened: [#472](https://github.com/Sturmi77/correlcore/issues/472)
- [ ] Product confirms §4 defaults (or records overrides in the issue)

**Exit:** Issue linked; defaults accepted or amended in writing.

### WP1 — Data window & control chrome

- Fix Compare shared-axis load to 365d
- Add `+/-` + status label above shared scroller (Co-Occurrence density pattern)
- Decide/hide range chips for Compare axis
- Persist `cc_trend_compare_zoom`

**Exit:** Controls visible on web + narrow viewport; stage persists; year data loaded.

### WP2 — Bucket axis + aggregations

- Implement `buildAxisBuckets`, heatmap sum, metric mean-with-coverage
- Relative colour scale on visible bucket max
- Partial bucket flags

**Exit:** Unit tests green; aggregations match fixtures for full and partial buckets.

### WP3 — Wire shared render path (Lines + Heatmap)

- Panel passes buckets to `MetricTimeseries` + `ComparisonHeatmap`
- Extend `timelineCursor` for bucket spans
- Keep single scroller sync

**Exit:** Zoom changes both layers together; cursor aligns; no desync under scroll.

### WP4 — Tap zoom-in + stage 0 sheet

- Multi-day tap → finer stage + scroll into view
- Day tap → existing sheet path
- Keyboard path: buttons focusable; optional arrow later

**Exit:** Component tests cover both tap modes; O-17 behaviour preserved at stage 0.

### WP5 — Interpretability UI

- Legend / encoding copy (sum vs mean)
- Tooltip: interval, sums, means, coverage, partial label
- i18n DE/EN
- No “KW” labelling

**Exit:** Copy review; tooltip fields asserted in tests where practical.

### WP6 — Strip mode & markers gate

- Until strip aggregation defined: either hide strip toggle while `stage > 0`,
  or force stage 0 when enabling strips
- Event markers / note dots: map to bucket containing the date
- Document follow-up: strip Z-score policy (mean of daily Z vs Z of bucket mean)

**Exit:** No dual-truth mode combination reachable in UI.

### WP7 — Capacitor / mobile QA

- Manual: Android (and iOS if available) WebView — `+/-`, scroll, tap zoom-in,
  stage 0 sheet, safe areas
- Confirm no need for Pinch; 44px targets on controls and cells
- Perf smoke: stage 0 scroll with typical row count

**Exit:** QA notes attached to issue; blockers filed or WP8 triggered.

### WP8 — Perf follow-up (only if WP7 fails)

- Column virtualisation and/or limit concurrent day-cells
- Or soft-cap: warn / keep minimum stage on low-end devices

**Exit:** Stage 0 usable on target device profile.

---

## 9. Acceptance criteria (v1)

1. With year data loaded, default view uses **7-day** columns (unless overridden
   by persisted stage).
2. `−` / `+` move through stages `1/3/7/14/28`; status text always reflects stage.
3. Heatmap and metric chart **always** share the same bucket columns and scroll
   position.
4. Heatmap cell = sum of daily counts; metrics = mean of days with entries;
   tooltips include coverage.
5. Partial edge buckets visible, labelled, not upscaled.
6. Tap multi-day bucket zooms in; tap day opens entry history.
7. Works in mobile browser and Capacitor without Pinch.
8. Strip/marker combinations cannot show conflicting granularities (WP6 gate).
9. Unit + component tests for bucket math, controls, and tap behaviour.
10. No new backend endpoint required.

---

## 10. Test plan (minimum)

| Layer           | Cases                                                                              |
| --------------- | ---------------------------------------------------------------------------------- |
| Unit            | Bucket boundaries from fixed `axisDates`; partial last/first; sum/mean; colour max |
| Component       | `+/-` clamps; persist mock; tap zoom-in; stage 0 `selectDate`                      |
| Panel           | Cursor store bucket span; scroll sync after zoom                                   |
| Manual / device | Capacitor scroll + zoom; tooltip readability; legend                               |

---

## 11. Out of scope (v1)

- Pinch-to-zoom / continuous scale
- Backend pre-aggregated granularity APIs
- Replacing Habit `TagHeatmap` or Symptom calendar heatmaps
- Calendar ISO-week alignment (Mo–So KW)
- Coverage heat overlay / second encoding channel (candidate v1.1)
- Long-press → entry sheet on buckets
- LayerChart adoption (still deferred per LayerChart plan)
- Parallel React GUI

---

## 12. Suggested GitHub issue shape

**Title:** `[FEATURE] Trends Compare: gemeinsame Achsen-Zoom-Stufen (Vogelperspektive)`

**Labels:** `enhancement`, `ux` (add `mobile` if used for Capacitor/PWA tracks)

**Body sections:** Problem / Motivation · Locked decisions (D1–D8) · Defaults (§4) ·
Risks R1–R10 with mitigations · Work packages WP0–WP8 · Acceptance criteria ·
Link to this plan · Datenschutz: no new data collection; client-side view over
existing entry stats.

---

## 13. Decision log

| Date       | Item           | Resolution                                         |
| ---------- | -------------- | -------------------------------------------------- |
| 2026-07-20 | Scope          | Compare shared axis only                           |
| 2026-07-20 | Zoom semantics | Display-only buckets; 365d load                    |
| 2026-07-20 | Heatmap agg    | Sum of occurrence                                  |
| 2026-07-20 | Metric agg     | Mean of days with entry                            |
| 2026-07-20 | Tap            | Zoom-in; sheet only at day stage                   |
| 2026-07-20 | Input          | `+/-` first; Capacitor required                    |
| 2026-07-20 | Risks          | R1–R10 folded into WPs + interpretability contract |

---

## 14. Open only if product overrides §4

1. Default stage 7 vs 1
2. Hide range vs keep parallel
3. Stage set 1/3/7/14/28 vs shorter 1/7/28
4. Zoom-in one stage vs jump to day

If no override is recorded before WP1, implement §4 as written.
