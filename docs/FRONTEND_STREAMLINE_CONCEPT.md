# Frontend Streamline Concept

Date: 2026-05-29

Updated: 2026-06-02 after mobile Erkenntnisse screenshot review.

## Objective

Raise the web frontend to a cleaner, more useful product level without changing
CorrelCore's core architecture:

- Home becomes a genuinely useful daily brief, not just an entry launcher.
- Insights stops repeating readiness, quality, and phase information.
- The insight phase model is visible once, clearly, and in the right place.
- Trends combines the trend chart and heatmap on one shared time axis.
- Heatmaps can include tags and symptoms, each switchable.
- The UI moves toward a calm, modern, analytical product surface.

## Current-State Findings

### Erkenntnisse Mobile Screenshot (2026-06-02)

The `/insights` mobile viewport was dominated by duplicated hierarchy:

- route title and subtitle
- a large readiness card headed "Vorlaeufige Erkenntnisse"
- a mixed control row combining view tabs and an independent symptom checkbox
- a second "Erkenntnisse" feed heading
- a large centered empty state

This made the first viewport feel like status and controls rather than a useful
findings surface. The accepted correction is findings-first: compact maturity
status, true view tabs, category filters inside the feed, and secondary analysis
behind disclosure.

### Home

`apps/web/src/routes/+page.svelte` already follows the documented "three
information zones" from `docs/FRONTEND.md`: today context, latest insight or
first-week banner, sparkline plus CTA.

The issue is not structural compliance. The issue is usefulness:

- `dashboardSummary` is loaded but barely used for user-facing value.
- The sparkline is visually present but does not answer "what should I notice?"
- The latest insight card is useful only when strong insights exist.
- The primary CTA dominates the value proposition, so Home still feels like an
  entry screen with a small preview attached.

### Insights

`apps/web/src/routes/insights/+page.svelte` stacks:

- optional `InsightPhaseMilestoneCard`
- `InsightJourneyBanner`
- `InsightMatrix`
- `InsightFeed`

Then `InsightFeed.svelte` renders `InsightQualityMeter` again above the cards.
This creates a valid but noisy screen: phase/progress/readiness are distributed
across multiple components, and "insight quality" competes with actual insights.

### Trends

`apps/web/src/routes/trends/+page.svelte` separates:

- Mood line chart under `Mood`
- Tag heatmap under `Activities`
- health consistency/cycle strip under `Health`
- habit detail under `Habits`

This makes each visualization simpler, but it blocks the user's main analytical
workflow: compare mood/energy/stress with what happened on the same days.
`TagHeatmap.svelte` already renders a date grid, but it has its own scroller and
time axis. `MetricTimeseries.svelte` uses the same date window concept but a
separate SVG axis. The data contracts currently support tag heatmaps only;
symptom heatmaps are not available through `stats.ts` yet.

## Design Principles

### Keep

- Exactly five primary screens. No new main navigation item.
- No gamification: no streak counters, rewards, urgency, or failure language.
- Progressive disclosure: overview first, details on interaction.
- Mobile-first with no horizontal overflow at 375 px.
- Existing shared primitives: `ScreenHeader`, `Panel`, `TabBar`,
  `SegmentedControl`, `DataState`/`EmptyState`/`InlineAlert`.

### Tighten

- One screen-level "status/readiness" object per screen. If the phase model is
  shown, quality/progress must not be restated elsewhere as another panel.
- Panels should be fewer and larger. Avoid stacking several separate cards that
  describe the same state.
- Tabs should represent distinct user questions, not implementation boundaries.
- Charts should share one time model when they are meant to be compared.

### Intentional Scope Shift

Symptom heatmap in Trends pulls part of `docs/DESIGN_DOCUMENT.md` symptom
visualization scope forward. The current document mentions symptom calendar and
trend visualizations as later work. If this is accepted, document it as a
frontend/API scope shift:

- acceptable: symptoms as neutral daily occurrence/intensity rows in the Trends
  comparison heatmap
- not included: symptom correlation engine, co-occurrence analytics, medical
  interpretation, diagnosis, or recommendations

This likely needs a short ADR or a `FRONTEND.md` update before implementation.

## Proposed Information Architecture

### Home: Daily Brief

Home stays one screen with three zones, but the zones change from "entry-first"
to "brief-first":

1. **Today Strip**
   - date
   - today's entry state
   - work context if known
   - compact edit/log action

2. **Daily Brief**
   - newest actionable insight when available
   - otherwise a readiness/phase message in one compact row
   - 7-day mood delta or "not enough data" state
   - top recent context: most frequent tag and notable symptom in the last 7 days

3. **Recent Pattern Preview**
   - compact 7-day mini timeline combining mood sparkline and daily entry dots
   - latest 2-3 entries as terse rows only if they add value
   - primary CTA remains visible but no longer consumes the whole screen

What this removes:

- Home should not show the full insight card anatomy.
- Home should not show the full phase journey.
- Home should not show a generic CTA block when today's entry already exists.

Target user question: "What is worth noticing today, and have I logged today?"

### Insights: One Phase Header, Then Findings

Insights should become:

1. **Insight Stage Header**
   - one compact horizontal component combining phase, current entries, next
     threshold, and readiness copy
   - expandable "how phases work" help
   - milestone message appears inline inside this component until dismissed

2. **Finding Controls**
   - filters: All, Mood, Symptoms, Sleep, Habits if useful
   - sort: strongest first remains default; optional sort can stay future work
   - disclaimer icon remains in header or control row

3. **Findings Feed**
   - cards focus on the actual insight statement
   - phase badge may appear on cards, but it must not restate the whole phase
     model

4. **Matrix As Detail, Not Main Competing Panel**
   - move `InsightMatrix` behind an "Explore matrix" disclosure or a secondary
     tab inside Insights
   - do not show matrix above the feed by default unless there are enough
     insights and the user opens it

What this removes:

- `InsightQualityMeter` as a separate component inside `InsightFeed`
- duplicate phase/readiness panels
- matrix before the user sees the actual findings

Target user question: "Which findings exist, and how mature is the evidence?"

### Trends: Compare Timeline

Replace the current separation of chart and heatmap with a primary Trends
comparison view:

1. **Shared Controls**
   - range: 7D, 30D, 90D, 1Y
   - metrics: Mood, Energy, Stress
   - rows: Tags, Symptoms
   - filters: tag category, symptom list, habit-only toggle where appropriate
   - Raw/Smoothed appears only for compatible ranges

2. **Unified Timeline Panel**
   - top: metric line chart
   - bottom: heatmap rows
   - one x-axis, one horizontal scroll container, one date selection model
   - clicking a chart point or heatmap cell opens the existing Entry History
     sheet

3. **Row Layer Model**
   - tag rows: same neutral blue intensity as today
   - symptom rows: separate neutral purple/blue intensity scale, based on max
     intensity/count in range
   - rows can be toggled by type and hidden individually

4. **Secondary Tabs**
   - `Compare` becomes the default Trends view
   - `Habits` can remain as a focused habit detail tab
   - `Health` should only contain cycle/context overlays that do not fit Compare
   - `Activities` as a standalone tab can be retired if Compare covers it

Potential naming:

- `Compare`
- `Habits`
- `Health`

This is a deliberate simplification from four tabs to three. It does not add a
primary screen, but it does change `FRONTEND.md`'s current Trends tab contract.

Target user question: "What happened on the same days as my mood/energy/stress
changes?"

## Data/API Plan

### Reuse Immediately

- `GET /api/v1/entries/stats/timeseries`
- `GET /api/v1/entries/stats/tags`
- `GET /api/v1/entries`
- `GET /api/v1/entries/{id}/symptoms`

### Add For Clean Implementation

Add a symptom heatmap endpoint rather than fetching symptoms entry-by-entry in
the Trends screen:

`GET /api/v1/entries/stats/symptoms?start_date=&end_date=`

Response shape should mirror tag heatmap but preserve intensity:

```json
{
  "start_date": "2026-05-01",
  "end_date": "2026-05-30",
  "symptoms": [
    {
      "symptom_id": "uuid",
      "slug": "headache",
      "name": "Headache",
      "days": [{ "date": "2026-05-12", "count": 1, "max_intensity": 2 }]
    }
  ]
}
```

Why not client-side aggregation:

- avoids N+1 entry symptom calls
- keeps privacy/logging concerns centralized in symptom service conventions
- makes mobile Trends reliable for 90D/1Y windows

### Optional Later

A combined endpoint can be added after the UI stabilizes:

`GET /api/v1/trends/compare?range=30&include=tags,symptoms`

Do not start here. It would overfit the API before the interaction model is
proven.

## Component Plan

### New / Refactored Components

- `HomeDailyBrief.svelte`
  - combines latest insight/readiness, 7-day delta, and notable recent context
- `InsightStageHeader.svelte`
  - replaces separate Journey Banner + Quality Meter surface
- `TrendsComparePanel.svelte`
  - owns unified line chart + heatmap layout
- `TimelineAxis.svelte`
  - shared date scale helpers for SVG line chart and heatmap grid
- `TrendLayerControls.svelte`
  - metrics, tag/symptom row toggles, filters
- `ComparisonHeatmap.svelte`
  - generalized heatmap row renderer for tag and symptom rows

### Existing Components To Simplify

- `InsightFeed.svelte`
  - remove `InsightQualityMeter`
  - remain focused on filters, error/empty/loading, and cards
- `InsightJourneyBanner.svelte`
  - either fold into `InsightStageHeader` or keep only as an explainer detail
- `InsightMatrix.svelte`
  - move behind disclosure/secondary view
- `MetricTimeseries.svelte`
  - extract geometry/date scaling into reusable utilities
- `TagHeatmap.svelte`
  - keep as compatibility wrapper or replace with `ComparisonHeatmap`
- `HomeSparkline.svelte`
  - can stay, but should become part of the daily brief rather than a standalone
    zone

## Visual Direction

Clean modern GUI here should mean:

- more editorial hierarchy, fewer equal-weight cards
- dense but calm operational surfaces
- clear section labels, restrained borders, fewer nested panels
- chart-first composition in Trends
- one canonical accent color, with neutral analytical scales
- no decorative hero, no marketing page, no bento-card dashboard

Concrete layout rules:

- Screen max width remains constrained, but Trends can use a wider chart canvas.
- Cards use 8 px or less radius unless existing tokens require otherwise.
- Avoid cards inside cards; use panels for major surfaces only.
- Compact labels inside panels; no hero-scale headings inside dashboards.
- Use icon buttons only for clear tools such as info, dismiss, expand, export.

## Implementation Sprints

### Sprint A - Decision & Contracts

- Update `docs/FRONTEND.md` with the new Home/Insights/Trends screen contracts.
- Add ADR or note for pulling symptom heatmap into Trends before later symptom
  visualization milestones.
- Define no-duplication rule: phase/readiness appears once per screen.
- Define accepted Trends tab structure.

Exit criteria:

- Scope is explicit.
- Any deviation from current documented Trends tabs is approved/documented.

### Sprint B - Insights First Viewport

- Compact `InsightStageHeader` so maturity is context, not the page's dominant
  card.
- Remove the duplicate feed-level "Insights" heading.
- Use `TabBar` for Findings/Matrix and keep category filters separate inside
  the feed.
- Move symptom context and tag co-occurrence behind a secondary analysis
  disclosure.
- Update tests around duplicate headings, route-local toggles, and compact
  empty states.

Exit criteria:

- One phase/readiness surface on `/insights`.
- Insight cards become the primary content again.
- At 375 px, the first viewport reaches findings or the empty-state explanation.

### Sprint C - Control System Enforcement

- Update `frontend/UI_COMPONENT_SYSTEM.md` with fixed control semantics.
- Treat route-local button groups, view toggles, and disabled placeholder
  buttons as legacy.
- Extend source contract tests for Insights, Trends, Settings, and Entry.

Exit criteria:

- New/refactored controls use shared primitives.
- Tabs, segments, switches, chips, buttons, and panels have distinct meanings.

### Sprint D - Useful Home

- Create `HomeDailyBrief`.
- Use existing entries, dashboard summary, and latest insight data to show:
  - today state
  - 7-day mood direction
  - latest useful insight or phase fallback
  - notable recent tag/symptom context when available
- Reduce CTA visual weight after today's entry exists.
- Keep entry sheet flow unchanged.

Exit criteria:

- Home answers "what is useful today?"
- CTA remains obvious but no longer monopolizes the screen.

### Sprint E - Trends Compare Foundation

- Extract shared date/geometry utilities from `MetricTimeseries` and
  `TagHeatmap`.
- Build `TrendsComparePanel` with line chart above heatmap rows.
- Use existing tag heatmap only first.
- Keep date selection wired to `EntryHistorySheet`.

Exit criteria:

- Mood/energy/stress and tags share one range and visual timeline.
- No horizontal overflow at 375 px.

### Sprint F - Symptom Heatmap

- Add backend symptom heatmap schema/service/endpoint.
- Add frontend API client and tests.
- Add Symptoms layer toggle to Trends Compare.
- Render symptom rows with neutral intensity scale and medical-neutral copy.

Exit criteria:

- Symptoms can be switched on/off in Trends heatmap.
- No medical interpretation is introduced.

### Sprint G - Entry, Settings & Visual QA

- Replace action-like route-local `.btn` usage in Entry and Settings with
  shared `Button`.
- Keep Entry chips limited to fast input selection.
- Replace disabled Settings placeholder buttons with passive planned-state text.
- Render QA at 375, 768, 1280 px in light and dark mode.
- Check Home, Insights, Trends, Entry Sheet, and Settings.
- Run no-gamification copy tests.
- Update `docs/FRONTEND.md`, changelog, and visual QA doc.

Exit criteria:

- No duplicate phase/readiness UI.
- No horizontal overflow.
- Interactions work with keyboard and touch.

## Critical Review

### Risk: Home Becomes Too Dashboard-Like

Making Home useful can easily turn it into another Trends/Insights summary.
Guardrail: Home only shows today's brief and the last 7 days. Anything requiring
filtering, drilling, or comparison belongs in Trends or Insights.

### Risk: Unified Trends Becomes Dense On Mobile

Line chart plus heatmap in one panel is the right analytical model but can be
too wide. Guardrail: one shared horizontal scroller, sticky row labels, and a
compact mobile row selector. Do not stack separate scroll areas.

### Risk: Symptom Heatmap Pulls M7 Too Early

Symptom visualization was previously future-scoped. Guardrail: implement only
daily occurrence/intensity rows. No symptom analytics, no co-occurrence claims,
no causal/medical copy.

### Risk: Removing Repetition Removes Reassurance

Phase/readiness repetition was probably added to increase trust. Removing it
must not hide uncertainty. Guardrail: one high-quality phase header, visible
disclaimer access, and maturity badges on cards only as compact context.

### Risk: Component Refactor Becomes Aesthetic Churn

"Clean modern" can become unfocused restyling. Guardrail: every change must
answer one of the product questions:

- Home: what is worth noticing today?
- Insights: what findings exist and how mature are they?
- Trends: what happened on the same days?

## Recommended First Implementation Slice

Start with **Insights Declutter** before Home or Trends.

Reasons:

- It directly addresses duplicated information.
- It is mostly frontend-only.
- It clarifies the phase model before Home reuses a compact phase fallback.
- It reduces screen noise without needing new backend endpoints.

Then implement Home Daily Brief, then Trends Compare, then Symptom Heatmap.
