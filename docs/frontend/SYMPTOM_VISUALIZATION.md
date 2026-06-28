# Symptom Visualization — Frontend Specification

> **Status:** Implemented (calendar + trend overlays, co-occurrence, descriptive heatmap) · **ADR:** [0025](../adr/0025-symptom-analytics.md) · **Feature Spec:** [`symptom-analytics.md`](../features/symptom-analytics.md) · **Last updated:** 2026-06-28

This document is the single source of truth for how symptom analytics is rendered, integrated, and
phase-gated across the CorrelCore frontend. It complements [`INSIGHT_MATURITY.md`](INSIGHT_MATURITY.md)
(maturity-phase mechanics) and the parent feature spec [`symptom-analytics.md`](../features/symptom-analytics.md)
(analytical methods and engine).

---

## 1. Component Inventory

| Component                      | Type               | Reuses                                 | Purpose                                                      |
| ------------------------------ | ------------------ | -------------------------------------- | ------------------------------------------------------------ |
| `SymptomAnalyticsSection`      | Container          | `ComparisonHeatmap`                    | Toggleable descriptive symptom history inside `/insights`    |
| `SymptomCooccurrenceHeatmap`   | Visualisation      | Existing custom SVG primitives         | Symptoms × Tags Lift-coloured grid                           |
| `SymptomCalendarHeatmap`       | Visualisation      | M2 `CalendarHeatmap` (data variant)    | Year-grid frequency view per symptom                         |
| `SymptomTrendOverlay`          | Visualisation      | `DualAxisChart` (FRONTEND.md §6.2)     | Rolling-7d symptom frequency + mood overlay                  |
| `SymptomInsightCard`           | Insight card       | `InsightCard` (progressive disclosure) | Card variant for symptom-derived insights                    |
| `SymptomMethodologyDisclaimer` | Modal/Bottom Sheet | `CorrelationDisclaimer` (extends)      | Symptom-specific methodology copy (esp. Lift interpretation) |

All components live under `apps/web/src/lib/components/insights/symptoms/` following the existing
folder convention for insight-related components.

**Implemented subset (2026-06-28):** `SymptomAnalyticsSection` renders the descriptive
`ComparisonHeatmap`, M7 `SymptomCooccurrenceHeatmap`, `SymptomCalendarHeatmap` (Monday-aligned
grid for symptoms with ≥5 occurrences), and `SymptomTrendOverlay` (rolling-7d frequency + mood).
Symptom history remains descriptive only. The co-occurrence grid renders backend-provided
Lift/count context without medical interpretation or recommendations.

---

## 2. Routing & Integration

Symptom analytics is integrated into the **existing `/insights` route**. **No separate
`/insights/symptoms` route is created** (per ADR-0025 decision).

### Page layout within `/insights`

```
┌─────────────────────────────────────────────────────────────┐
│  InsightJourneyBanner                       (existing)      │
├─────────────────────────────────────────────────────────────┤
│  InsightFeed                                (existing)      │
│    ↳ InsightCard items, including SymptomInsightCard        │
│      variants mixed inline with tag/metric insights         │
├─────────────────────────────────────────────────────────────┤
│  Symptom Analytics Section          (toggleable, gated)     │
│    ┌─────────────────────────────────────────────────────┐  │
│    │  Heatmap, co-occurrence, calendar, and trend views   │  │
│    └─────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  InsightMatrix                              (existing)      │
└─────────────────────────────────────────────────────────────┘
```

**Section position:** below `InsightFeed`, above `InsightMatrix`. Rationale: the feed remains the
primary surface for user attention; the new symptom section is a deeper-exploration area for users
who want to drill down. The matrix stays at the bottom as the existing reference view.

**Section visibility:** the entire "Symptom Analytics Section" container is hidden in `collecting`.
Below that, individual components have their own phase gates (see §6).

**User toggle:** `/insights` exposes a "Blend in symptoms" toggle persisted in
`cc_insights_symptoms`. Turning it off hides the descriptive section without affecting generated
insight cards or analytics settings.

**Mixed insight stream:** `SymptomInsightCard` variants appear **interleaved** with existing
`InsightCard` items in `InsightFeed`. Sorting follows the existing `confidence × effect_size` rule
from [ADR-0017](../adr/0017-frontend-screen-architecture.md). Symptom cards are not visually
separated or grouped.

**Current feed compatibility:** until the backend emits symptom-specific cards, the `Symptoms` tab
matches both legacy metric strings and future payload shapes (`insight_type`, `subject_type`,
`subject_label`, payload/flag `kind`) so the feed can accept `symptom_*` insight types without a
route change.

---

## 2.1 Implemented descriptive symptom context

`SymptomAnalyticsSection` is the first shipped frontend slice of symptom visualisation:

- Route: existing `/insights`, below `InsightFeed` in the findings view.
- Data: `fetchSymptomHeatmap({ start_date, end_date })` for the same 90-day context used by the
  insights page.
- Rendering: `ComparisonHeatmap` with symptom rows only.
- Phase: hidden in `collecting`; visible from `early_patterns` onward when the user toggle is on.
- Semantics: descriptive frequency/intensity context only; no statistical claims.
- Tests: `InsightFeed` includes future symptom insight payload filtering; shared heatmap rendering is
  covered through the trends comparison component and chart utilities.

---

## 3. `SymptomCooccurrenceHeatmap`

### Structure

```
              Tag A  Tag B  Tag C  Tag D  Tag E
Symptom 1     [ 1 ] [2.4*] [0.8 ] [1.0 ] [0.5*]
Symptom 2     [3.1*] [1.2 ] [0.9 ] [1.5 ] [0.7 ]
Symptom 3     [0.6 ] [1.0 ] [2.0*] [0.3*] [1.1 ]

  Cell  = Lift value
  *     = FDR-significant (p_adj < 0.10)
  Color = divergent blue (Lift < 1) / neutral (Lift ≈ 1) / red (Lift > 1)
```

### Props

```typescript
interface SymptomCooccurrenceHeatmapProps {
  data: CooccurrenceCell[];
  symptoms: SymptomLabel[];
  tags: TagLabel[];
  phase: 'early_patterns' | 'provisional' | 'robust';
  sortMode?: 'alphabetical' | 'clustered';
  onCellClick?: (cell: CooccurrenceCell) => void;
}

interface CooccurrenceCell {
  symptom_id: string;
  tag_id: string;
  lift: number;
  phi: number;
  jaccard: number;
  co_count: number;
  symptom_count: number;
  tag_count: number;
  total_count: number;
  p_value_corrected: number | null;
  confounder: 'weekday' | null;
}
```

### Visual Rules

| Aspect              | Rule                                                                                                     |
| ------------------- | -------------------------------------------------------------------------------------------------------- |
| Color scale         | Divergent: blue (`--color-info`) for Lift < 1, white at Lift = 1, red (`--color-warning`) for Lift > 1   |
| Color clamp         | Lift ≤ 0.33 = max blue; Lift ≥ 3.0 = max red; values outside clamp use clamp color                       |
| Cell annotation     | `co_count` as small subscript number in bottom-right of cell                                             |
| Significance marker | `*` after Lift value when `p_value_corrected < 0.10`                                                     |
| Confounder marker   | Cell uses muted/desaturated variant when `confounder === 'weekday'`                                      |
| Empty cells         | Pairs not meeting eligibility threshold: rendered as crosshatch pattern with tooltip "Insufficient data" |
| Cell size           | 48×48 px desktop, 40×40 px mobile, with 1px gap                                                          |
| Axis labels         | Truncated with ellipsis at 12 chars; full name in tooltip                                                |
| Mobile labels       | 375 px uses compact horizontal labels in a local scroller; rotated headers must not overlap grid cells   |

### Phase-Gated Rendering

| Phase            | Rendering                                                                                             |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| `collecting`     | Component not rendered (hidden by parent section gate)                                                |
| `early_patterns` | Renders **raw counts only** — no Lift colouring, no significance markers, neutral grey scale          |
| `provisional`    | Full Lift colouring, FDR significance markers, confounder muting                                      |
| `robust`         | Full Lift colouring, plus optional hierarchical clustering reordering when `sortMode === 'clustered'` |

### Display Filtering (from Feature Spec)

- Cell rendered with colour when `|Lift − 1| > 0.5` OR `p_value_corrected < 0.10`
- Below threshold: cell shown but rendered in neutral grey (visual de-emphasis, not hidden — users
  should see the full landscape)

### Sorting

- **Default:** alphabetical by symptom name on Y, tag name on X
- **Clustered (toggle, `robust` only):** hierarchical clustering on Jaccard distance reorders both
  axes so co-occurring groups visually cluster (analogous to bioinformatics heatmap conventions)

### Interaction

- Click on cell → opens detail modal with all metrics (Phi, Jaccard, Lift, Fisher Exact, co_count,
  base rates) and a "Why this matters" explanation
- Detail modal links to `SymptomMethodologyDisclaimer` for methodology background
- Tooltip on hover: "Symptom X occurred with Tag Y on 9 of 12 symptom days"

### Accessibility

- Cell content readable by screen reader: full numeric values + interpretation phrase
- Color scale is supplemented with text (Lift value always visible), not colour-only
- Keyboard navigation: arrow keys move focus across cells, Enter opens detail modal

---

## 4. `SymptomCalendarHeatmap`

A year-grid view (GitHub-style contribution graph) showing symptom presence per day, one heatmap per
symptom.

### Structure

```
Symptom: Headache · 47 occurrences in last 365 days

Jan  ▢▢▢▣▢ ▢▢▢▢▢ ▣▢▢▢▢ ▢▢▢▣▣ ▢▢▢▢▢ ...
Feb  ▢▢▣▢▢ ▢▢▢▢▢ ▢▣▢▢▢ ▢▢▢▢▢ ▢▣▢▢▢ ...
...

  ▢ = no symptom    ▣ = symptom present
```

### Props

```typescript
interface SymptomCalendarHeatmapProps {
  symptomId: string;
  symptomName: string;
  data: DailyOccurrence[];
  phase: 'early_patterns' | 'provisional' | 'robust';
  yearOffset?: number; // 0 = current year, -1 = previous, default 0
}

interface DailyOccurrence {
  date: string; // ISO yyyy-mm-dd
  present: boolean;
}
```

### Visual Rules

- Reuses the M2 `CalendarHeatmap` SVG primitive but with **binary** present/absent rendering (the
  M2 component supports a frequency gradient; symptom variant uses only two states)
- Color: present cells use `--color-warning` at 100% opacity, absent cells use `--color-surface-2`
- Cell size: 12×12 px desktop, 10×10 px mobile
- Day-of-week labels on left (Mon–Sun), month labels above
- Total occurrence count shown in header for context

### Phase-Gated Rendering

| Phase            | Rendering                                                                       |
| ---------------- | ------------------------------------------------------------------------------- |
| `collecting`     | Component not rendered                                                          |
| `early_patterns` | **Renders fully** — pure descriptive visualisation, no statistical claim        |
| `provisional`    | Same as `early_patterns`, plus inline note: "Now showing in correlations below" |
| `robust`         | Same as `provisional`                                                           |

This is the only symptom component that is fully visible from `early_patterns` — frequency
visualisation does not make any correlation claim and is therefore statistically uncontroversial.

### Which Symptoms Are Shown

- Only symptoms meeting the min-frequency threshold (≥ 5 occurrences in the displayed period)
- Sorted by total occurrences descending
- Maximum 8 heatmaps rendered to prevent overwhelming the UI; remaining symptoms accessible via
  a "Show all" expansion

### Interaction

- Click on a day cell → opens entry drawer for that date (existing pattern from `/entries`)
- Hover tooltip: full date + symptom status

### Accessibility

- Each cell has aria-label: "2026-03-14, Headache present"
- Keyboard navigation: arrow keys move focus within the grid

---

## 5. `SymptomTrendOverlay`

A dual-axis line chart showing rolling-7-day symptom frequency overlaid with rolling-7-day mood
average. Wraps the existing `DualAxisChart` component (FRONTEND.md §6.2).

### Structure

```
Symptom: Headache · Last 60 days

Frequency           Mood
   1.0                 10
        ╭─╮                            ─── Headache freq (left)
   0.5         ╭───╮      6        ─── Mood avg (right)
        ╯           ╰╮
   0.0  ───────────────╰──────  2
        Mar 1   Mar 15   Apr 1
```

### Props

```typescript
interface SymptomTrendOverlayProps {
  symptomId: string;
  symptomName: string;
  data: TrendPoint[];
  phase: 'early_patterns' | 'provisional' | 'robust';
  rollingWindowDays?: number; // default 7
  showUncertaintyRibbon?: boolean; // default true in non-robust phases
}

interface TrendPoint {
  date: string;
  symptomFrequency: number; // rolling-7d, range 0..1
  moodAverage: number | null; // rolling-7d, range 1..10, null if no entries
  moodUncertainty?: number; // standard error for ribbon
}
```

### Visual Rules

- Left axis: symptom frequency (0–1)
- Right axis: mood (1–10)
- Symptom line: solid, `--color-warning`
- Mood line: solid, `--color-mood-primary` (violet, per ADR-0020)
- Uncertainty ribbon: shaded area around mood line when `showUncertaintyRibbon === true` (per
  ADR-0018 and the cross-cutting "uncertainty ribbon" gap identified in M3.6 audit)
- X-axis: last 60 days by default, configurable
- Both lines use the same theme tokens as existing charts; no new colour tokens introduced

### Phase-Gated Rendering

| Phase            | Rendering                                                                                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- |
| `collecting`     | Component not rendered                                                                                              |
| `early_patterns` | Renders with uncertainty ribbon on mood line; no statistical annotation                                             |
| `provisional`    | Renders with uncertainty ribbon; optional inline annotation when associated insight exists ("Linked to insight: X") |
| `robust`         | Renders without uncertainty ribbon (mood data is sufficiently stable); insight annotation visible                   |

### Which Symptoms Are Shown

- Same filtering as `SymptomCalendarHeatmap`: ≥ 5 occurrences, sorted by total frequency descending
- Maximum 4 trend overlays rendered; rest via "Show all"

### Accessibility

- Chart has aria-label describing both series
- Data table fallback available via keyboard shortcut (existing pattern from M2 charts)

---

## 6. `SymptomInsightCard`

A variant of the existing `InsightCard` (FRONTEND.md, ADR-0017) tailored for symptom-derived
insights. Appears interleaved with other insight cards in `InsightFeed`.

### Variants by Insight Type

| Insight Type                | Card Title Pattern                             | Primary Statement Pattern (provisional)                                               |
| --------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| `symptom_mood_association`  | "{Symptom} days and your {metric}"             | "On days with {symptom}, your {metric} tends to be lower."                            |
| `symptom_tag_cooccurrence`  | "{Symptom} often coincides with {tag}"         | "When you log {symptom}, {tag} is present {jaccard\*100}% of the time."               |
| `symptom_cluster` (lasso)   | "{Symptom} stands out in your overall pattern" | "Among many factors, {symptom} is one of the strongest links to your {target}."       |
| `symptom_cluster` (lag)     | "{Symptom} relates to next-day {target}"       | "{Symptom} days are followed by lower {target} the next day."                         |
| `symptom_cluster` (cluster) | "{Symptom} appears with related signals"       | "{Symptom}, {co-cluster member 1}, and {co-cluster member 2} tend to occur together." |

All copy templates live in `i18n/insights/symptoms/*.json` with the namespace `insight.symptom.*`.

### Progressive Disclosure (per ADR-0017)

Three levels, identical mechanism to existing `InsightCard`:

- **Level 1 (collapsed):** title + primary statement + `InsightMaturityBadge`
- **Level 2 (expanded):** plus effect size in plain language ("Strong association" / "Moderate
  association" / "Weak association" — see effect size mapping below), plus sample size, plus link
  to `SymptomMethodologyDisclaimer`
- **Level 3 (deep dive):** plus mini-chart (sparkline of symptom frequency over time, or mini
  co-occurrence cell highlight), plus list of "evidence days" (latest 5 dates where the pattern
  was observed)

### Effect Size to Plain Language Mapping

For `symptom_mood_association` (using Cliff's Delta as the robust effect size):

| `           | δ                                         | `   | Label |
| ----------- | ----------------------------------------- | --- | ----- |
| < 0.147     | Negligible (suppressed in card surfacing) |
| 0.147–0.330 | Small association                         |
| 0.330–0.474 | Moderate association                      |
| ≥ 0.474     | Strong association                        |

For `symptom_tag_cooccurrence` (using Lift):

| Lift Range | Label                           |
| ---------- | ------------------------------- |
| 0.67–1.5   | Suppressed in card surfacing    |
| 1.5–2.0    | "Often occurs together"         |
| 2.0–3.0    | "Frequently occurs together"    |
| ≥ 3.0      | "Almost always occurs together" |
| 0.33–0.67  | "Rarely occurs together"        |
| < 0.33     | "Almost never occurs together"  |

### Phase Behaviour

- `collecting`: card not produced by engine, not rendered
- `early_patterns`: card not produced by engine for symptom insights (descriptive components only)
- `provisional`: card renders with `InsightMaturityBadge` showing "Provisional · N entries" and
  cautious copy tone
- `robust`: card renders with confident copy tone; uncertainty disclaimer no longer in collapsed
  state (still accessible in expanded state)

### Confounder Handling

When `payload.confounder === 'weekday'`:

- Card renders with a muted variant (reduced contrast, smaller badge)
- Subtitle line added: "Note: this pattern is also linked to a weekday effect."
- Card is downgraded in the feed sort order (sorted after non-confounded insights of the same
  effect size)

---

## 7. `SymptomMethodologyDisclaimer`

Extension of the existing `CorrelationDisclaimer` modal. Adds two new sections explaining
symptom-specific methodology.

### New Sections

#### "How we look at symptoms"

Plain-language explanation of:

- Why presence/absence (binary) is used rather than intensity
- What "association" means and why it does not mean causation
- What FDR correction does ("we account for the fact that we run many checks")

#### "Reading the Lift number"

Lift is non-intuitive. The disclaimer must explain:

- Lift = 1 means "no special connection"
- Lift = 2 means "twice as likely to co-occur than chance" (NOT "twice as likely overall")
- Lift = 0.5 means "half as likely to co-occur than chance"
- Always pair with co-occurrence count for context ("seen together on 9 of 12 headache days")

### Structure

```
┌─ Methodology ──────────────────────────────────────────┐
│  How insights are computed             [existing copy]  │
│  How confidence works                  [existing copy]  │
│                                                          │
│  How we look at symptoms               [NEW]            │
│  Reading the Lift number               [NEW]            │
│                                                          │
│  [Close]                                                 │
└──────────────────────────────────────────────────────────┘
```

### Trigger Points

- Link from every `SymptomInsightCard` expanded state: "How do we know this?"
- Link from `SymptomCooccurrenceHeatmap` header: "What do these numbers mean?"
- Link from `SymptomTrendOverlay` legend: "Why is there a shaded area?"

---

## 8. Affected UI Elements — Full Map

| Element                               | Location                             | Adaptation                                                         |
| ------------------------------------- | ------------------------------------ | ------------------------------------------------------------------ |
| Symptom Analytics Section (container) | `/insights` route                    | Hidden in `collecting`; visible from `early_patterns` onward       |
| `SymptomCooccurrenceHeatmap`          | Symptom Analytics Section            | Hidden in `early_patterns` for Lift; renders raw counts only       |
| `SymptomCalendarHeatmap`              | Symptom Analytics Section            | Renders from `early_patterns`; max 8 visible without expansion     |
| `SymptomTrendOverlay`                 | Symptom Analytics Section            | Renders from `early_patterns` with uncertainty ribbon              |
| `SymptomInsightCard`                  | `InsightFeed` (inline)               | Produced by engine from `provisional` onward                       |
| `SymptomMethodologyDisclaimer`        | Modal triggered from multiple places | Always available; extends existing `CorrelationDisclaimer`         |
| Insight feed sorting                  | `InsightFeed`                        | Confounded symptom insights sorted lower than non-confounded peers |
| `CorrelationDisclaimer`               | Existing modal                       | Extended with two new sections                                     |
| Empty state (Symptom Analytics)       | Symptom Analytics Section            | Phase-aware: "Track 7+ days to see symptom patterns"               |

---

## 9. Copy Guidelines

### Tone per phase (symptom-specific)

| Phase            | Symptom analytics tone                                                                            |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| `collecting`     | Nothing shown — no symptom copy at all                                                            |
| `early_patterns` | Observational, descriptive: "You've logged headache 7 times. Patterns may emerge with more data." |
| `provisional`    | Cautious, qualified: "Early signal: headache often coincides with high-stress tags."              |
| `robust`         | Confident, neutral: "Headache and high-stress tags consistently co-occur."                        |

### Forbidden language

- ❌ "X causes Y"
- ❌ "Avoid X to feel better"
- ❌ "You should..."
- ❌ "Diagnosis", "symptom of", "indicator of [medical condition]"
- ❌ "Significant" (without qualifier — too easily read as "important" vs. "statistically significant")

### Preferred language

- ✅ "X often coincides with Y"
- ✅ "Days with X tend to..."
- ✅ "When X is present, Y is more common"
- ✅ "X and Y appear together more than chance"
- ✅ "Worth noting" / "Worth a closer look"

### Translation keys (`i18n`)

```
insight.symptom.mood_association.title
insight.symptom.mood_association.statement.provisional
insight.symptom.mood_association.statement.robust
insight.symptom.mood_association.confounder.weekday

insight.symptom.tag_cooccurrence.title
insight.symptom.tag_cooccurrence.statement.provisional
insight.symptom.tag_cooccurrence.statement.robust
insight.symptom.tag_cooccurrence.confounder.weekday

insight.symptom.cluster.lasso.title
insight.symptom.cluster.lasso.statement
insight.symptom.cluster.lag.title
insight.symptom.cluster.lag.statement
insight.symptom.cluster.cluster.title
insight.symptom.cluster.cluster.statement

symptom.analytics.section.title
symptom.analytics.section.empty.collecting
symptom.analytics.section.empty.early_patterns
symptom.cooccurrence.heatmap.title
symptom.cooccurrence.heatmap.legend.lift
symptom.cooccurrence.heatmap.legend.significance
symptom.calendar.heatmap.title
symptom.trend.overlay.title
symptom.trend.overlay.legend.uncertainty

symptom.methodology.binary_presence
symptom.methodology.association_not_causation
symptom.methodology.fdr_correction
symptom.methodology.lift_explanation
symptom.methodology.lift_example_high
symptom.methodology.lift_example_low

symptom.effect.negligible
symptom.effect.small
symptom.effect.moderate
symptom.effect.strong
symptom.effect.lift.often
symptom.effect.lift.frequently
symptom.effect.lift.almost_always
symptom.effect.lift.rarely
symptom.effect.lift.almost_never
```

All keys must be defined in both `de` and `en` per CorrelCore i18n conventions.

---

## 10. API Contract (Frontend Perspective)

The frontend consumes the new insight type strings defined in
[`symptom-analytics.md`](../features/symptom-analytics.md) §API Contract:

- `symptom_mood_association`
- `symptom_tag_cooccurrence`
- `symptom_cluster`

For the `SymptomCooccurrenceHeatmap`, an additional aggregated payload structure is required from
the backend. The exact endpoint and shape is defined in the feature spec; for the frontend, the
expected response shape is:

```typescript
interface SymptomCooccurrenceMatrix {
  symptoms: SymptomLabel[];
  tags: TagLabel[];
  cells: CooccurrenceCell[]; // sparse — only computed pairs
  insight_maturity: InsightMaturity; // from ADR-0021
}
```

The frontend MUST NOT compute phase or significance independently — both come from the API
response (consistent with ADR-0021).

---

## 11. Acceptance Criteria

### Routing & Integration

- [x] No `/insights/symptoms` route exists
- [x] Symptom Analytics Section renders below `InsightFeed` within the existing `/insights` route
      when the findings view is active
- [x] Descriptive symptom section can be toggled by the user and is persisted locally
- [ ] `SymptomInsightCard` items appear interleaved in `InsightFeed`, sorted by
      `confidence × effect_size` alongside other insight cards

### `SymptomCooccurrenceHeatmap`

- [ ] Divergent Lift colour scale renders correctly with neutral at Lift = 1
- [ ] Cell annotation shows `co_count` as subscript
- [ ] FDR significance marker (`*`) appears when `p_value_corrected < 0.10`
- [x] Confounder muting applies when `confounder === 'weekday'`
- [ ] In `early_patterns`: only raw counts rendered, no Lift colouring
- [x] In `robust`: clustered sort mode available via toggle
- [ ] Cell click opens detail modal with all metrics
- [ ] Cell tooltips include base-rate context phrase
- [ ] Keyboard navigation works (arrow keys + Enter)
- [ ] Screen reader reads cell content correctly

### `SymptomCalendarHeatmap`

- [ ] Reuses M2 `CalendarHeatmap` primitive (binary variant)
- [ ] Renders from `early_patterns` phase
- [ ] Maximum 8 heatmaps shown by default; "Show all" expansion works
- [ ] Click on day cell opens entry drawer for that date
- [ ] Only symptoms with ≥ 5 occurrences in the period are shown

### `SymptomTrendOverlay`

- [ ] Uses existing `DualAxisChart` component
- [ ] Symptom and mood lines render with correct colour tokens
- [ ] Uncertainty ribbon visible in `early_patterns` and `provisional`
- [ ] Uncertainty ribbon hidden in `robust`
- [ ] Default 60-day window; configurable
- [ ] Maximum 4 overlays shown by default

### `SymptomInsightCard`

- [ ] Three progressive disclosure levels work (collapsed / expanded / deep dive)
- [ ] Title and statement patterns match the table per insight type
- [ ] Effect size shown as plain-language label, never as raw number in collapsed state
- [ ] `InsightMaturityBadge` integrated and phase-appropriate
- [ ] Confounder variant renders muted with explanatory subtitle
- [ ] Card sort order respects confounder downgrade

### `SymptomMethodologyDisclaimer`

- [ ] Extends existing `CorrelationDisclaimer` (does not duplicate it)
- [ ] "How we look at symptoms" section present
- [ ] "Reading the Lift number" section present with examples for Lift > 1 and Lift < 1
- [ ] Trigger links present in card expanded state, heatmap header, and trend overlay legend

### Copy & i18n

- [ ] All `insight.symptom.*` and `symptom.*` translation keys defined in `de` and `en`
- [ ] No forbidden language patterns appear in any rendered copy
- [ ] Tone matches phase per the tone guidelines table

### Phase Gating

- [x] In `collecting`: entire Symptom Analytics Section is hidden
- [ ] In `early_patterns`: only descriptive views render (calendar heatmap, raw-count co-occurrence,
      trend overlay); no Lift colouring, no insight cards
- [ ] In `provisional`: full statistical rendering with FDR markers and uncertainty ribbons
- [x] In `robust`: confident copy, optional clustered sort, no uncertainty ribbon on trend overlay
- [ ] Phase is always read from API `insight_maturity.phase` — never recomputed in frontend

### Cross-cutting

- [ ] No raw p-values surfaced to user anywhere
- [ ] All chart colour usage respects ADR-0020 (no red/green encoding for value judgement; Lift
      heatmap explicitly violates this with documented justification — divergent scale is
      necessary for bidirectional association and uses warning/info tokens, not red/green)
- [ ] All new components have `data-testid` attributes for E2E test coverage

### Implemented 2026-05-30 subset

- [x] `/trends` Compare uses a shared daily axis for trendline and tag/symptom heatmap rows
- [x] `/trends` tag and symptom context layers are independently toggleable and persisted
- [x] `/insights` includes toggleable descriptive symptom history via `SymptomAnalyticsSection`
- [x] `InsightFeed` symptom filtering recognises future symptom insight payloads

---

## 12. Open Questions

- **ADR-0020 exception**: The divergent Lift heatmap uses warning/info colour tokens that visually
  resemble red/green. ADR-0020 explicitly states heatmaps should use neutral blue scales. This
  spec proposes a documented exception because bidirectional association (Lift < 1 and Lift > 1
  carry equally important meaning) cannot be expressed in a sequential scale. **Decision needed
  before M7 implementation starts.**
- **Insight feed mixing vs. grouping**: The current spec interleaves symptom insight cards with
  other insights. Alternative (rejected for now): group symptom cards into a "Symptom insights"
  collapsible subsection within the feed. Revisit if user testing shows symptom cards drown in
  the feed.

---

## 13. Related Documents

- [ADR-0017](../adr/0017-frontend-screen-architecture.md) — Frontend screen architecture (5 primary screens)
- [ADR-0018](../adr/0018-insight-confidence-visualisation.md) — Confidence visualisation
- [ADR-0020](../adr/0020-primary-color-system.md) — Primary color system (heatmap colour rules)
- [ADR-0021](../adr/0021-insight-maturity-phases.md) — Insight maturity phases
- [ADR-0025](../adr/0025-symptom-analytics.md) — Symptom analytics architectural decision
- [`INSIGHT_MATURITY.md`](INSIGHT_MATURITY.md) — Maturity rendering conventions (sibling document)
- [`../features/symptom-analytics.md`](../features/symptom-analytics.md) — Parent feature spec
- [`../FRONTEND.md`](../FRONTEND.md) — Overall frontend architecture (§6.2 DualAxisChart reference)
