# ADR-0035: Temporal Correspondence Pattern for Trends ↔ Tags/Symptoms

| Field        | Value                                                                |
| ------------ | -------------------------------------------------------------------- |
| **ID**       | 0035                                                                 |
| **Date**     | 2026-05-30                                                           |
| **Status**   | Proposed                                                             |
| **Deciders** | @Sturmi77                                                            |
| **Area**     | Frontend / Visualisation / Architecture                              |
| **Supersedes** | Partially supersedes [ADR D-002](../DESIGN_DOCUMENT.md#7) (chart-library policy) |

---

## Context

### The problem statement

The `/trends` Compare view aligns the Mood/Energy/Stress line chart and the
Tag/Symptom heatmap rows onto a **shared ISO daily axis** (FRONTEND.md §Screen 4).
This geometric co-location was a first step that established the visual
substrate. User feedback (2026-05-30) confirms that the alignment by itself does
**not yet enable temporal pattern recognition**: users see two charts on the same
axis but cannot easily perceive whether a tag or symptom episode coincides with,
precedes, or follows a change in continuous metrics.

The remaining gap is the **temporal correspondence problem**: the cognitive cost
of saccading between a dip in the line chart and a darker cell in a heatmap row
exceeds what is acceptable for the core insight workflow. This is well documented
in the information visualisation literature on superimposed time-series and
temporal event sequences.

### Research foundation

Four research streams inform this decision:

1. **Event-sequence alignment.** Zhang et al. (IEEE VIS 2019)[¹] empirically
   compared four alignment strategies for superimposed time-series + event data:
   no-alignment (NoAlign), single-event-alignment (SingleAlign), and two
   dual-event variants. **Single-event alignment** wins decisively for
   precursor/aftereffect questions ("what happens around event X"). **NoAlign**
   wins for duration questions ("how long did the low-mood cluster last"). No
   single layout serves both — the application must offer a switch between
   chronological and event-centred views.

2. **Lasagna plots beat spaghetti plots beyond a few rows.** Swihart et al.
   (Epidemiology 2010)[²] introduced the lasagna plot — a heatmap with one row
   per longitudinal subject/variable and colour encoding the outcome. Tangke
   et al. (2025)[³] and Jiménez & Macías (Computer Graphics Forum 2022)[⁴]
   confirm that beyond ~5 parallel rows, line overlays suffer from over-plotting
   while lasagna plots remain readable, especially when combined with **dynamic
   row sorting** (correlation-sorted, cluster-sorted).

3. **Multi-visualisation orchestration for behaviour-change apps.** Bell et al.
   (JMIR 2020, n = 19 233)[⁵] explicitly conclude that a single visualisation
   systematically misses patterns in self-tracking data; their Drink-Less app
   study used four complementary forms (heatmap, timeline, k-modes clustering,
   Kaplan-Meier). The implication for CorrelCore: temporal correspondence is
   not solved by one chart, but by an orchestrated **layered set**.

4. **Mobile visualisation constraints.** Brehmer et al. (TVCG 2019)[⁶] show
   small multiples beat animation on mobile for trend comparison.
   Hosseinpour et al. (TVCG 2024)[⁷] show comprehension accuracy declines
   linearly with the number of frames — practical mobile limit is ~3 panels at
   375 px width.

### Existing decisions to revisit

This ADR explicitly puts three previously-accepted decisions on the table:

| Decision | Status before this ADR | Re-evaluation outcome |
| -------- | --------------------- | --------------------- |
| **D-002 — Custom-SVG only, no chart library** | Accepted (rationale: bundle-size budget < 150 KB gz, dark-mode token control, colour-blind safety via dash patterns) | **Partially superseded.** Tree-shakable chart libraries now exist (LayerChart ≈ 60 KB gz, uPlot ≈ 45 KB gz) that fit the budget. Hidden maintenance cost of custom SVG (current `MetricTimeseries.svelte` already 398 LOC) outweighs the bundle savings as analytical complexity grows. |
| **No-Gamification — no red/green traffic-light colouring (DESIGN_DOCUMENT §1.4)** | Accepted | **Reaffirmed and clarified.** The rule is preserved but restated in **theme-agnostic, hue-family terms** so future GUI re-themes (different primary hue families) remain conformant. |
| **Compare view: lines above heatmap rows (FRONTEND.md §Screen 4)** | Accepted as default | **Reaffirmed as default, but supplemented** by a Unified-Strip alternative mode for parity-of-encoding. |

---

## Decision

We adopt a **three-layer Temporal Correspondence Pattern** for the Trends and
Insights routes, with a controlled, partial relaxation of D-002.

### Layer 1 — Synchronised Cursor + Event Markers (Stage 1)

A shared timeline cursor (`TimelineCursor` store, fields `{ x, date, source }`)
is consumed by `MetricTimeseries` and `ComparisonHeatmap`. A tap, drag, or
keyboard navigation on either component drives a vertical line through both,
plus a floating detail card listing all metric values and active
tags/symptoms for the selected date.

Additionally, user-pinned **event markers** (small glyphs on the metric lines)
indicate dates when a chosen tag or symptom was active. Pin set is limited to
3 simultaneously (Hosseinpour 2024 cognitive limit).

**Implementation:** Custom SVG only. No new library dependency. Touches existing
components.

### Layer 2 — Unified-Strip Render Mode + Library Adoption (Stage 2)

`MetricTimeseries` gains a render-mode toggle `Lines | Strips`. In Strip mode,
each metric is rendered as a horizontal heatmap row with a **divergent scale**
encoding Z-score against the user's personal rolling baseline mean. This puts
Mood/Energy/Stress, Tags, and Symptoms into identical geometric encoding —
enabling true 1:1 column-wise comparison, which is the core lasagna-plot
advantage (Swihart 2010).

Layer 2 adopts **LayerChart** as the chart library for this milestone.
Rationale, alternatives evaluated, and the partial supersession of D-002 are
documented in §_Chart Library Selection_ below.

Heatmap rows (tags, symptoms, metric strips) gain a **dynamic sort mode**
(default: alphabetical; alternative: sort by absolute pointbiserial correlation
to currently focused metric, descending). Sort mode persists in
`cc_trend_compare_sort`.

### Layer 3 — Event-Aligned Small-Multiples Sheet (Stage 3)

Tap on a tag, symptom, or pinned event opens a secondary sheet (in line with
ADR-0017 — no new route) showing small multiples of all Mood/Energy/Stress
trends, **each centred on every occurrence of the event** (Tag 0 = event day,
window ±7 days, configurable to ±14). A median line across occurrences is
overlaid. This is the Single-Event-Alignment configuration shown empirically
best for precursor/aftereffect questions (Zhang et al. 2019).

Phase-gated: visible only from insight phase `provisional` onward
(ADR-0021), with appropriate confidence and base-rate disclaimers
(ADR-0018, [`docs/frontend/SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md)
patterns).

### Theme-agnostic colour semantics for divergent scales

The No-Gamification rule from DESIGN_DOCUMENT §1.4 is preserved. To make it
robust against future GUI re-themes (potentially with a different primary hue
family than the current violet system documented in ADR-0020 and ADR-0026), the
rule is restated **structurally** rather than against any specific hue:

> A divergent visualisation scale used to encode signed magnitude (e.g.
> Z-score deviation from baseline, positive vs. negative correlation) must
> consist of either:
>
> - **(a)** a single hue family with two perceptual extremes (light vs. dark, or
>   desaturated vs. saturated), **or**
> - **(b)** two hues drawn from the active theme's accent system that are
>   **not** perceptually red↔green and **not** culturally readable as a
>   traffic-light verdict.
>
> Specifically: the pair (red ≈ H 0°/360°, green ≈ H 120°) and any pair within
> 20° of those hues is forbidden in the same scale. The two endpoints of a
> divergent scale must come from the theme's defined `--color-divergent-neg`
> and `--color-divergent-pos` tokens. Theme authors are free to pick any
> conformant pair when designing a new theme.

This formulation:

- Does not bind CorrelCore to a specific palette (violet, blue, or otherwise).
- Lets any future theme (e.g. orange-based, teal-based, or a customer-branded
  variant) define its own conformant divergent scale.
- Preserves the strategic No-Gamification differentiator against
  Bearable/Daylio-style streak/ampel aesthetics.

The two new tokens are added to the theme contract:

```css
/* Required in every theme — both modes */
--color-divergent-neg: /* one endpoint of divergent scales */;
--color-divergent-pos: /* the other endpoint */;
--color-divergent-mid: /* neutral midpoint, typically equal to --color-surface */;
```

The current violet/dark theme will populate these tokens during Stage 2; the
specific values are a theming concern, not an architectural one, and are
deferred to [`COLOR_SCHEME_CONCEPT.md`](../frontend/COLOR_SCHEME_CONCEPT.md).

### Chart Library Selection

D-002 (Custom-SVG only) is **partially superseded** by this ADR. Custom SVG
remains the default for simple primitives (sparklines, M2 calendar heatmap,
existing tag heatmap, status meters). For the analytical deep views in
`/trends` and `/insights` (synchronised cursors across multiple panes, unified
strip rendering, small multiples, future lag-correlation heatmaps), a
tree-shaken chart library is now permitted, with a **hard marginal bundle
budget of 80 KB gz** above the current baseline.

Alternatives evaluated:

| Library                 | Bundle (gz, tree-shaken for our use) | SvelteKit-SSR fit                          | Heatmap support       | Sync cursor across charts | Licence    | Verdict                    |
| ----------------------- | ------------------------------------ | ------------------------------------------ | --------------------- | ------------------------- | ---------- | -------------------------- |
| **LayerChart**          | ≈ 55–65 KB                           | ✅ Native Svelte 5, SSR-friendly           | ✅ Built-in           | ✅ Built-in `<Tooltip>` connector | MIT        | **Chosen**                 |
| uPlot                   | ≈ 45 KB                              | ⚠️ Canvas-only, needs SSR shim             | ⚠️ Requires custom plugin | ⚠️ Manual               | MIT        | Rejected (no heatmap)      |
| ECharts (tree-shaken)   | ≈ 110–130 KB                         | ⚠️ Canvas, needs lifecycle wiring          | ✅ Native             | ✅ `connect()` API        | Apache 2.0 | Rejected (budget pressure) |
| Plotly.js (basic-dist)  | ≈ 280 KB                             | ⚠️ Heavy                                   | ✅                    | ✅                        | MIT        | Rejected (budget violation) |
| Vega-Lite               | ≈ 200 KB                             | ⚠️ Heavy, declarative paradigm clash       | ✅                    | ⚠️ Cross-spec wiring      | BSD        | Rejected (budget violation) |

**Chosen: LayerChart.** Reasons:

1. **Svelte 5-native** — no wrapper layer, no React/Vue compatibility tax.
2. **SSR-friendly** — works with SvelteKit's adapter-node setup unchanged.
3. **Token-aware** — accepts CSS custom properties directly, preserving the
   ADR-0020/0026/0027 token discipline.
4. **Built-in cursor synchronisation** between multiple chart contexts, which
   is precisely the Layer 1 primitive we need.
5. **Within the 80 KB marginal budget** with room to spare.
6. **Heatmap component** native, so Layer 2 (unified strip mode) does not need
   a custom implementation.

### Compare view layout: default and alternative

The current layout (Mood/Energy/Stress **lines above** Tag/Symptom heatmap rows,
shared daily axis) **remains the default** for first-time users and for the
`collecting` and `early_patterns` insight phases. Rationale: lines are the most
recognisable form for the headline metrics, and the asymmetry signals "mood is
the outcome, tags are context", which matches the analytical mental model.

A new **Unified-Strip Mode** becomes available as a user-selectable alternative
in Layer 2. In this mode, Mood/Energy/Stress are also rendered as heatmap strips
above the tag and symptom rows, all using identical geometric encoding. This
mode is recommended (and pre-selected if the user has > 12 active tags) for
multi-variable comparison tasks.

Toggle state persists in `cc_trend_compare_mode` (values: `lines` | `strips`).

---

## Consequences

### Benefits

- **Direct addressing** of the temporal correspondence problem in three
  complementary ways (cursor for active exploration, strips for passive
  pattern detection, small multiples for analytical drill-down).
- **No new architectural concept** — every layer reuses or extends existing
  primitives (`MetricTimeseries`, `ComparisonHeatmap`, secondary sheets per
  ADR-0017, phase gating per ADR-0021).
- **Future-theme-safe colour semantics** — divergent-scale tokens decouple the
  architecture from any specific palette. The current violet/dark theme and any
  future GUI re-skin remain conformant by following the structural rule.
- **No-Gamification differentiator preserved** in stronger, theme-agnostic form.
- **Mobile-first respected** — every layer works under one controlled horizontal
  scroller with sticky labels.

### Costs and risks

- **D-002 partial supersession.** The repository ceases to be a 100 % custom-SVG
  visualisation system. Mitigated by a hard marginal bundle budget (80 KB gz)
  and confining the library to `/trends` and `/insights` deep views.
- **Bundle-size CI gate must be extended** to track the marginal cost of
  LayerChart imports. A new pnpm script `pnpm check:bundle:trends` is added
  during Stage 2.
- **Two compare modes (lines vs. strips)** double the visual QA surface for
  this screen. Mitigated by Playwright snapshot tests for both modes and a
  shared layout primitive.
- **Library lock-in.** Switching away from LayerChart later would require
  reimplementing Stage 2/3 visualisations. Mitigated by isolating LayerChart
  imports behind a thin wrapper module
  (`apps/web/src/lib/charts/adapter/index.ts`) so a future swap touches one
  module rather than every chart.

### Migration and rollout

- Layers ship **sequentially** in three sub-sprints (see [`M3_8_SPRINT_PLAN.md`](../M3_8_SPRINT_PLAN.md)).
  Per Space convention, no parallel work on chart components across sub-sprints.
- D-002 entry in DESIGN_DOCUMENT §7 is updated to reference this ADR and reflect
  the partial supersession.
- FRONTEND.md §Screen 4 is updated to describe the Lines/Strips dual-mode and
  the layered correspondence pattern.
- DESIGN_DOCUMENT §1.4 is updated to use the theme-agnostic divergent-scale
  formulation.

---

## Alternatives rejected

- **Bearable-style gradient backdrop only.** Coloured vertical bands behind the
  lines work for ≤ 3 tags but break visually with the CorrelCore tag counts
  typical at insight phase `provisional`+ (often 10–30 active tags). Rejected
  as a sole solution; remnants survive as the optional pinned-event marker
  pattern in Layer 1.
- **Horizon charts.** High information density per pixel ([Okai-Nóbrega et al.
  2021, MethodsX](https://pmc.ncbi.nlm.nih.gov/articles/PMC8374341/)), but the
  double-folding of the Y-axis with colour encoding is consistently rated
  hard-to-learn for non-expert users — unacceptable for a consumer self-tracking
  PWA.
- **ThemeRiver / Streamgraph of tag frequencies.** Strong gestalt perception
  of "tag waves" but requires substantial horizontal width — incompatible
  with the 375 px mobile constraint from DESIGN_DOCUMENT §2.10.
- **Full ECharts adoption.** Solves every visualisation problem but breaks the
  bundle-size budget even tree-shaken when multiple chart types are needed.
- **Continued strict D-002 (no library).** Would force Layers 2 and 3 to be
  implemented from scratch in SVG, with conservative estimate of +800–1200 LOC,
  much of it duplicated cross-component logic (tick computation, hover state,
  touch handling, A11y labels, test coverage). Decision: this hidden
  maintenance cost outweighs the bundle savings of staying library-free.

---

## References

[¹] Yixuan Zhang, Sara Di Bartolomeo, Fangfang Sheng, Holly Jimison, Cody Dunne.
"Evaluating Alignment Approaches in Superimposed Time-Series and Temporal
Event-Sequence Visualizations." IEEE VIS 2019. DOI:
[10.1109/VISUAL.2019.8933584](https://doi.org/10.1109/VISUAL.2019.8933584).

[²] Bruce J. Swihart et al. "Lasagna Plots: A Saucy Alternative to Spaghetti
Plots." _Epidemiology_ 21(5), 2010.
[PMC2937254](https://pmc.ncbi.nlm.nih.gov/articles/PMC2937254/).

[³] Tangke et al. "Analisis Komparatif Lasagna Plots dan Spaghetti Plots."
JISAMAR 9(4), 2025. DOI: [10.52362/jisamar.v9i4.2108](https://doi.org/10.52362/jisamar.v9i4.2108).

[⁴] Edgar Jiménez, Roberto Macías. "Graphical Tools for Visualization of
Missing Data in Large Longitudinal Phenomena." _Computer Graphics Forum_
41(1), 2022. DOI: [10.1111/cgf.14445](https://doi.org/10.1111/cgf.14445).

[⁵] Lauren Bell, Claire Garnett, Tianchen Qian et al. "Engagement With a
Behavior Change App for Alcohol Reduction: Data Visualization for Longitudinal
Observational Study." _JMIR_ 22(12), 2020. DOI:
[10.2196/23369](https://doi.org/10.2196/23369).

[⁶] Matthew Brehmer, Bongshin Lee, Petra Isenberg, Eun Kyoung Choe. "A
Comparative Evaluation of Animation and Small Multiples for Trend Visualization
on Mobile Phones." IEEE TVCG 2019. DOI:
[10.1109/TVCG.2019.2934397](https://doi.org/10.1109/TVCG.2019.2934397).

[⁷] Helia Hosseinpour, Kristin M. Divis, Lace M. Padilla et al. "Examining
Limits of Small Multiples: Frame Quantity Impacts Judgments With Line Graphs."
IEEE TVCG 2024. DOI:
[10.1109/TVCG.2024.3372620](https://doi.org/10.1109/TVCG.2024.3372620).

## Related ADRs

- [ADR-0017](0017-frontend-screen-architecture.md) — Frontend screen architecture
  (secondary sheets, no new routes for drill-downs)
- [ADR-0018](0018-insight-confidence-visualisation.md) — Confidence visualisation
- [ADR-0020](0020-primary-color-system.md) — Primary colour system
- [ADR-0021](0021-insight-maturity-phases.md) — Insight maturity phases
- [ADR-0025](0025-symptom-analytics.md) — Symptom analytics
- [ADR-0026](0026-color-scheme-evaluation-orange-vs-violet.md) — Colour scheme evaluation
- [ADR-0027](0027-light-mode-color-requirements.md) — Light mode requirements

## Related Documents

- [`DESIGN_DOCUMENT.md`](../DESIGN_DOCUMENT.md) §2.10, §7 (D-002), §1.4
- [`FRONTEND.md`](../FRONTEND.md) §Screen 4 (Trends)
- [`COLOR_SCHEME_CONCEPT.md`](../frontend/COLOR_SCHEME_CONCEPT.md)
- [`SYMPTOM_VISUALIZATION.md`](../frontend/SYMPTOM_VISUALIZATION.md)
- [`M3_8_SPRINT_PLAN.md`](../M3_8_SPRINT_PLAN.md) — execution plan
