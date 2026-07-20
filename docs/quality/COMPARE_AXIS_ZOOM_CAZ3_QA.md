# Compare Axis Zoom — CAZ-3 QA Checklist

**Feature:** Trends Compare shared-axis bird’s-eye zoom  
**Tracker:** [#472](https://github.com/Sturmi77/correlcore/issues/472)  
**Sprints:** CAZ-1 [#480](https://github.com/Sturmi77/correlcore/pull/480) · CAZ-2 [#481](https://github.com/Sturmi77/correlcore/pull/481) · CAZ-3 [#483](https://github.com/Sturmi77/correlcore/pull/483)  
**Date:** 2026-07-20

Manual checks for Web / PWA / Capacitor WebView. Automated coverage notes are
inline. Device rows need a physical or emulator pass before closing #472.

---

## Automated (CI / vitest)

| Check | Result |
| --- | --- |
| Bucket math, sum/mean, clamp | Pass (`compareAxisZoom.test.ts`) |
| Persist default stage 7 | Pass (`comparePanelSettings.test.ts`) |
| Shared axis zoom +/- | Pass (`TrendsComparePanel.test.ts`) |
| Tap multi-day → zoom-in; day → selectDate | Pass |
| Strip mode resets coarse zoom + disables zoom controls | Pass (CAZ-3 tests) |
| Heatmap bucket tooltips / coverage | Pass |
| Compare loads year; range chips hidden | Pass (`page.test.ts`) |
| Marker dedupe helper | Pass (`EventMarkerLayer` / unit coverage) |

No Pinch gesture is implemented (by design).

---

## Manual device / WebView checklist

Run: Capacitor Android (preferred) or mobile Safari/Chrome on `pnpm dev` /
preview build. Clear site data once for default-stage check.

| # | Check | Pass? | Notes |
| --- | --- | --- | --- |
| 1 | `+/-` reachable, controls ≥ 44px (`--tap-target`) | ☐ | CSS uses `min-width/min-height: var(--tap-target)` |
| 2 | Horizontal scroll does not trigger accidental zoom | ☐ | Zoom only via buttons / cell tap |
| 3 | Tap zoom-in works with touch on multi-day cell | ☐ | |
| 4 | Stage 0 tap opens Entry history sheet | ☐ | |
| 5 | Partial bucket readable (opacity + tooltip `k of N`) | ☐ | |
| 6 | After clear storage: year data + default **7 days / cell** | ☐ | |
| 7 | Persist stage after app background / resume | ☐ | `cc_trend_compare_zoom` |
| 8 | Stage 0 scroll performance OK with typical row count | ☐ | If fail → Slice F |
| 9 | Switch Lines → Strips while zoomed: reset notice + day columns | ☐ | |
| 10 | In Strips: zoom `+/-` disabled; hint visible | ☐ | |

**Slice F trigger:** If row 8 fails on target device, open perf follow-up
(virtualisation or soft-cap min stage) — do not block v1 docs closeout for
other rows.

---

## Follow-ups

- Strip Z-score bucket aggregation (mean of daily Z vs Z of bucket mean) —
  tracked as a separate enhancement after CAZ-3.
- Habit / symptom-calendar heatmaps out of scope.

---

## Sign-off

| Role | Name | Date | Result |
| --- | --- | --- | --- |
| Implementer (automated) | cloud agent | 2026-07-20 | Automated rows Pass |
| Device QA | _pending_ | | |
