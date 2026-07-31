warning: encountered old-style '//SynologyDS923/docker/dockhand/git-repos/Synolgy DS923+/correlcore' that should be '%(prefix)///SynologyDS923/docker/dockhand/git-repos/Synolgy DS923+/correlcore'

# CorrelCore — Frontend Principles

Derived from [`DESIGN_DOCUMENT.md`](DESIGN_DOCUMENT.md). Last updated: 2026-05-31 (M7 mobile insight hardening — metadata, tabs, co-occurrence matrices, bottom sheets).

> **Note:** This document supersedes the previous version. The old home-screen sketch showing `[Streak: 🔥 7]` has been removed — it contradicted the No-Gamification Promise (§1.4 DESIGN_DOCUMENT). See [ADR-0017](adr/0017-frontend-screen-architecture.md).

## Mobile/Web Operating Model (2026-06-22)

- **Mobile is the daily-use surface:** capture, check-in, quick feedback, and lightweight review.
- **Web is the analysis surface:** comparison, management, deeper review, and data-dense visualisation.
- **One SvelteKit codebase:** routes, API contracts, stores, validation, and domain calculations stay shared.
- **Composition differs by surface:** mobile uses single-column flows and focused drill-downs; desktop may use split views, side panels, sticky controls, and wider chart regions.
- **Existing shell breakpoint:** bottom navigation changes to the desktop rail at the global `768px` breakpoint.
- **No compressed desktop dashboards on mobile:** Trends and Insights expose summaries plus focused details instead of full desktop parity.

**Current status snapshot (2026-06-27):**
[`frontend/FRONTEND_STATUS.md`](frontend/FRONTEND_STATUS.md) — deploy readiness,
route matrix, quality gates, and deferrals.

The complete audit and delivery sequence are maintained in
[`frontend/MOBILE_WEB_AUDIT.md`](frontend/MOBILE_WEB_AUDIT.md) and
[`frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md`](frontend/MOBILE_WEB_IMPLEMENTATION_PLAN.md).
Editable Figma references are linked from those documents.

---

## 1. Core Principles

### 1.1 Analytical Clarity over Aesthetic Delight

CorrelCore is not a wellness journal. The visual language must signal **precision and trustworthiness**, not playfulness. The color palette (`--color-primary: #7c6af5 / #6356d9`) is technical and modern. Charts use semantic colors (negative correlation → desaturated cool tones, positive → warm primary tones), never arbitrary brightness.

> **Color note:** `--color-primary` uses a violet palette, intentionally diverging from the Nexus design system defaults (teal). This decision reflects the analytical/technical brand direction (§1.1) and is formalized in [ADR-0020](adr/0020-primary-color-system.md).

### 1.2 The 60-Second Rule

The default daily entry must be completable in ≤ 60 seconds:

- Mood slider (required)
- Work context quick-pick (one tap)
- Top 3 tags (optional, pre-sorted by usage frequency)
- Symptoms / Note (optional, behind "More" expand)

Every component that slows this flow must be reconsidered.

### 1.3 Progressive Disclosure — Three Levels

All insight content follows a strict 3-level disclosure model:

| Level               | Content                                                   | Trigger            |
| ------------------- | --------------------------------------------------------- | ------------------ |
| **1 — Statement**   | One-sentence finding + direction indicator                | Always visible     |
| **2 — Context**     | Confidence bar + sample_n + time window + disclaimer link | Visible on card    |
| **3 — Exploration** | Full dual-axis chart, raw data overlay, export button     | Tap "Show details" |

No user should need Level 3 to understand the value of an insight.

### 1.4 Data Integrity as UX Statement

Every insight card **must** carry:

- `confidence` visualised as a labelled progress bar (see §6)
- `sample_n` as subtext (`Based on 42 entries · 90 days`)
- A "What does this mean?" link to the correlation disclaimer

This is active user trust-building, not legal boilerplate.

### 1.5 No-Gamification Consequences in Visualisations

- **No** streak counters anywhere in the UI
- **No** badges, points, fire emojis, or reward animations
- Calendar / frequency heatmaps use a **theme-agnostic single-hue neutral scale** sourced from `--color-heatmap-*` tokens — never a red/green traffic-light pair that implies a streak verdict. The active hue is owned by the GUI theme (see [`COLOR_SCHEME_CONCEPT.md`](frontend/COLOR_SCHEME_CONCEPT.md)); components must not hardcode a hue. See [ADR-0035](adr/0035-temporal-correspondence-pattern.md) for the divergent-scale rule.
- Habit adherence is shown as a **percentage rate**, not a chain counter
- Notifications copy is always neutral: "Time for your daily check-in." — never "Don't break your streak!"
- **InsightQualityMeter copy is always descriptive, never imperative.** No call-to-action, no urgency framing. Example of correct copy: _"At your current tracking pace: ca. 2–3 weeks until first insight."_ — no emoji, no imperative verb. See Issue #184.

### 1.6 Mobile First

- Breakpoints: 360 px (mini) → 480 px (narrow) → 768 px (shell) → 1024 px+ (wide)
- Touch targets: ≥ 44 × 44 px (WCAG 2.5.5); dense heatmap matrix cells ≥ 24 px hit-area via padding/`::after` without enlarging the visible cell
- Bottom sheet instead of full-page navigation for entry creation
- Every screen must render without horizontal scroll at 360 px
- Within-screen filter tabs use horizontal scrolling on narrow screens instead of wrapping into
  disjoint rows. Page-level horizontal scroll remains forbidden; overflow must stay inside the
  control or chart/table scroller.
- Dense analytical matrices may use internal horizontal scrolling at 360 px, but row labels, column
  labels, and legends must remain visually attached to the data they describe.
- Mobile bottom sheets must account for `env(safe-area-inset-bottom)` in their panel padding and
  must not leave a dead grey block below the actionable sheet content.

### 1.7 Offline-Ready Component Contract

Every data-fetching component must define all four states:

```
Loading → Skeleton placeholder
Error   → Inline error + retry button
Empty   → Contextual empty state (not a blank div)
Offline → Cached data with "offline" badge or graceful hide
```

---

## 2. Tech Stack

| Technology                | Rationale                                                 |
| ------------------------- | --------------------------------------------------------- |
| **SvelteKit 2**           | Smallest bundle, SSR/CSR flexible, native transitions     |
| **Skeleton UI**           | SvelteKit-native, themeable, dark-mode support            |
| **Dexie.js**              | IndexedDB abstraction for offline sync (active from M4)   |
| **Custom SVG components** | Chart library (D-002 decided — see DESIGN_DOCUMENT §2.10) |
| **pnpm + Vite**           | Fast HMR, optimised bundling, pinned via ADR-0010         |
| **svelte-i18n**           | Current i18n implementation for DE + EN                   |

> **i18n implementation note (Issue #185):** M3.5 uses the existing `svelte-i18n` setup. Do **not** introduce a second custom writable locale store. Language switching should update the active `svelte-i18n` locale, persist a local fallback, and sync to the server only once a `locale` user-preference field exists. A future migration to `paraglide-js` requires a dedicated ADR and must not be mixed into the language-toggle sprint.

---

## 3. Performance Budget

| Metric                         | Target   |
| ------------------------------ | -------- |
| JS Bundle (gzipped)            | < 150 KB |
| LCP (Largest Contentful Paint) | < 2.0 s  |
| TTI (Time to Interactive)      | < 3.0 s  |
| CLS                            | < 0.1    |
| FID / INP                      | < 100 ms |

Enforced via Lighthouse CI in the CI/CD pipeline. Web Vitals monitoring via GlitchTip.

---

## 4. Design System

### 4.1 Theming

Color tokens are defined in `apps/web/src/app.css`.
Light mode requirements are formally specified in
[ADR-0027](adr/0027-light-mode-color-requirements.md). The theoretical
framework and contrast tables are documented in
[COLOR_SCHEME_CONCEPT.md](frontend/COLOR_SCHEME_CONCEPT.md).

```css
:root[data-theme='dark'] {
  --color-bg: #171614;
  --color-surface: #221f1c;
  --color-primary: #7c6af5;
  --color-text: #cdccca;
  --color-text-muted: #878684;
}

:root[data-theme='light'] {
  --color-bg: #fafaf7;
  --color-surface: #ffffff;
  --color-primary: #6356d9;
  --color-text: #1c1a17;
  --color-text-muted: #6b6660;
}
```

- System preference via `prefers-color-scheme` as default
- Manual override via `data-theme` attribute on `<html>`
- Persisted in LocalStorage
- `pnpm check:contrast` verifies the ADR-0027 text/UI token pairs in CI.
- `--color-text-faint` is reserved for decorative or placeholder states only.

### 4.2 Mood Score Colours

Mood, energy, and stress are stored on a **1–5 Likert scale** (see `ENTRY_CONTRACT` / `lib/config/metrics.ts`). Charts and strips encode values with **metric tokens**, not a red/green traffic-light pair:

| Metric | Token                   | Role                                                                |
| ------ | ----------------------- | ------------------------------------------------------------------- |
| Mood   | `--color-metric-mood`   | Primary mood line / strip encoding                                  |
| Energy | `--color-metric-energy` | Energy line / strip encoding                                        |
| Stress | `--color-metric-stress` | Stress line / strip encoding (view-layer invert via `invert: true`) |

Divergent encodings (e.g. event-aligned small multiples, ADR-0035) use the chart adapter’s midpoint/range mapping — never hardcoded hue literals in components.

Colour must **never** be the only information carrier — always pair with label or icon (WCAG 1.4.1).

### 4.3 Metric Semantics & Invert Flag

Not all metrics share the same direction — a higher raw value does not always mean "better". The following table is the canonical definition for chart rendering, analytics worker correlation sign, and axis labelling:

| Metric | DB field     | Scale | Direction       | `invert` | Notes                            |
| ------ | ------------ | ----- | --------------- | -------- | -------------------------------- |
| Mood   | `mood_score` | 1–5   | Higher = better | `false`  |                                  |
| Energy | `energy`     | 1–5   | Higher = better | `false`  |                                  |
| Stress | `stress`     | 1–5   | Higher = worse  | `true`   | Issue #182 — display = `6 - raw` |

> **Implementation:** The `invert` flag is defined centrally in `src/lib/config/metrics.ts` and consumed by `MetricTimeseries.svelte`, `DualAxisChart.svelte`, and `analytics_worker.py`. Raw DB values are **never** modified — inversion is view-layer only.

### 4.4 Confidence Bar (Insight-Specific)

Insight confidence is visualised as a single-colour progress bar with a semantic label. No stars (gamification association), no raw percentages on cards (pseudo-precision). See [ADR-0018](adr/0018-insight-confidence-visualisation.md).

```
confidence  bar fill    label
0.0–0.2     ██░░░░░░░░  Early signal
0.2–0.4     ████░░░░░░  Emerging pattern
0.4–0.6     ██████░░░░  Moderate finding
0.6–0.8     ████████░░  Strong finding
0.8–1.0     ██████████  Very strong finding
```

- Bar uses `--color-primary` at varying opacity
- Label text is intentionally epistemological, not evaluative
- Raw `confidence` value and `sample_n` shown in Level 2 / expanded state only

### 4.5 UI Component Contract

All new controls and screen-level refactors must follow the shared component contract in [`frontend/UI_COMPONENT_SYSTEM.md`](frontend/UI_COMPONENT_SYSTEM.md). Route-local button, tab, panel, and header styling is legacy unless a component has an explicit exception.

Mandatory shared primitives for the next frontend hardening work:

- `Button` / `IconButton` for all actions, including text links that behave like controls
- `ScreenHeader` for primary screen headers
- `Panel` for bounded information and tool surfaces
- `SegmentedControl` and `TabBar` for filters and within-screen views
- `BottomSheet` for entry creation and secondary mobile flows
- `DataState`, `EmptyState`, and `InlineAlert` for loading, error, empty, and offline states

Every interactive primitive must provide a 44 x 44 px touch target, visible focus state, accessible label, and a documented variant/state model.

### 4.6 GUI Consolidation Contract

Accepted 2026-06-02 after mobile review of the Erkenntnisse screen.

Every primary screen follows the same hierarchy:

1. One screen title via `ScreenHeader`
2. At most one compact status/control row before content
3. The screen's main value in the first mobile viewport
4. Secondary depth behind tabs, disclosure, or sheets

Control vocabulary is fixed:

- `TabBar` switches in-screen views.
- `SegmentedControl` chooses one exclusive filter or mode.
- Checkbox/switch controls independent layers or persistent settings.
- Chips are fast content selection, mainly inside entry flows.
- Buttons are actions or action-like links; disabled placeholders must not look like actions.

Insights is the reference implementation: the maturity phase is context, not the
main content. Findings or a compact empty state must appear before matrix,
symptom, or co-occurrence analysis surfaces.

---

## 5. Screen Architecture

CorrelCore has exactly **5 primary screens**. No screen may be added without an explicit justification and ADR entry. See [ADR-0017](adr/0017-frontend-screen-architecture.md).

M5 Streamline keeps that contract intact: matrix views, entry details, comparison layers, and analysis drilldowns are secondary sheets, panels, tabs, or query-state views inside the existing routes. Mobile-first defines prioritization and touch flow; desktop may use split views, sticky controls, and side panels to preserve data depth without adding primary screens.

> **Naming note:** All sub-views, history lists, and calendar overlays within a screen are **secondary sheets or tabs** — they do not constitute separate primary screens. The Entry History view (tap on a past entry) is a secondary sheet overlay within Trends, not a standalone screen.

### Screen 1: Home (`/`)

**Purpose:** Daily touch point. Create or edit today's entry and receive a compact Daily Brief.

**M5 Streamline:** Home is not a mini-dashboard. It has a fixed Today Strip, configurable compact blocks (Daily Brief, work-context summary, weekday overview — see `/settings/home`), and a primary CTA. Full filters, matrices, and raw analytics live in Insights or Trends drilldowns.

**Layout:** Fixed Today Strip at the top, configurable compact blocks in the
middle (user order via `/settings/home`), primary CTA at the bottom when today
is not logged yet.

```
┌──────────────────────────────┐
│  Wednesday, 13 May           │  ← Fixed: HomeTodayContext
│  [🏠 Home office]            │     (date, work context, edit action)
│                              │
│  ┌────────────────────────┐  │
│  │ DAILY BRIEF            │  │  ← Configurable blocks (default order):
│  │ Top insight or phase   │  │     1. FirstWeekInsightBanner*
│  │ [Explore insights →]   │  │     2. HomeDailyBrief
│  └────────────────────────┘  │     3. HomeWorkContextSummary
│  ┌────────────────────────┐  │     4. HomeWeekdayOverview
│  │ WORK CONTEXT PATTERN   │  │     * banner only when data + pref enabled
│  └────────────────────────┘  │
│  ┌────────────────────────┐  │
│  │ WEEKDAY OVERVIEW       │  │
│  └────────────────────────┘  │
│                              │
│  ┌─────────────────────────┐ │
│  │  + Log today            │ │  ← Fixed: primary CTA (if !todayEntry)
│  └─────────────────────────┘ │
└──────────────────────────────┘
```

**Rules:**

- No streak counter — tracking consistency widget (neutral %) only when relevant
- Home does not dismiss insights directly; insight-level actions live in `/insights`.
- `FirstWeekInsightBanner` is configurable (`first_week_banner`) and still data-gated
- Insight fetch is best-effort and must not block the primary CTA
- Home must not render insight maturity journey banners, phase milestone cards, insight matrices, deep filters, or secondary navigation that duplicates `AppNav`.
- Home shows a short insight summary or phase fallback in `HomeDailyBrief`, not the full `InsightCard` anatomy. Bridge links drill down to `/insights` and `/trends`.
- No sparkline, recent-entries grid, or summary matrix on Home — those belong under Trends / Insights.
- Desktop may place Today Strip and Brief side by side. Mobile remains one column with the CTA visible; after today's entry exists, "Edit today" is visually lighter than the initial log action.
- Layout customization: Settings → Appearance → **Home layout** (`/settings/home`); persisted in `user_preferences.home_sections` (see ADR-0017 amendment #584).

---

### Screen 2: Entry Form (Bottom Sheet, triggered from Home)

**Purpose:** Log daily entry in ≤ 60 seconds.

**Layout:**

```
┌──────────────────────────────┐
│  ▬  How was your day?        │
│                              │
│  ●─────────────────── ○      │  ← Mood slider (1..5)
│  Bad              Very good  │
│                              │
│  Energy  ●────────── ○       │
│  Stress  ○──────────●        │  ← Stress: higher raw = worse (invert: true)
│                              │
│  [🏠 Home] [🏢 Office] [✈️] │  ← Work context quick-pick
│                              │
│  [Sport ] [Music ] [+ More ] │  ← Top tags + expand
│                              │
│  [Save]                      │  ← Auto-save (ADR-0013)
└──────────────────────────────┘
```

**Rules:**

- Mood slider is the only required field
- Tag suggestions sorted by historical usage frequency
- "+ More" opens time-slot chips, cycle day, full tag sheet, symptoms and notes; photo upload follows in M13
- The full `TagPicker` supports inline custom tag creation in the entry/edit flow: name, category,
  unique slug, optional icon and colour. A newly-created tag is added to the in-memory catalogue and
  selected immediately when the entry has not reached `MAX_TAGS_PER_ENTRY`.
- Day-over-day delta shown as neutral info card after save (Issue #154)
- Time slots use the existing API field `slot`: `day` means whole-day; `morning`, `noon`, and `evening` are optional chips.
- `cycle_day` is optional, accepts `1..35`, and is framed as neutral personal context only.
- Stress slider axis label reflects inverted semantics: left = "High stress", right = "Low stress"

---

### Screen 3: Insights (`/insights`)

**Purpose:** Explore all generated insights with progressive disclosure and a single readiness surface.

**M5 Streamline:** `InsightStageHeader` is the only default phase/readiness surface. It replaces separate journey banner, quality meter, and standalone milestone card presentation. `InsightMatrix` remains available as a secondary drilldown, not as default viewport content.

**GUI consolidation update (2026-06-02):** The maturity surface is compact on
mobile: phase, entry count, next threshold, progress, and help affordance in one
status row. The feed no longer renders a second screen-level "Insights" heading.
`Findings` and `Matrix` are view tabs; metric/category filters remain inside the
feed. Symptom context and tag co-occurrence are secondary analysis surfaces below
the default findings flow or behind disclosure.

**Layout:**

```
┌──────────────────────────────┐
│  Insights                    │
│  Last 90 days · n=67 entries │
│                              │
│  Insight Quality              │  ← Readiness meter from recent entries
│  [██████░░░░] 18/30           │
│                              │
│  [All][Mood][Symptoms][Sleep] │  ← Metric filter tabs
│  [x] Blend in symptoms        │  ← Toggleable descriptive symptom context
│                              │
│  ┌────────────────────────┐  │
│  │ ↗ POSITIVE             │  │
│  │ Exercise → Mood        │  │
│  │ Provisional · 42 entries │ │
│  │ "On exercise days..."  │  │
│  │ Based on 42 entries    │  │
│  │ [Show details ▼]       │  │
│  └────────────────────────┘  │
│  ...                         │
└──────────────────────────────┘
```

**Rules:**

- Sorted by `confidence × effect_size` descending (strongest, most certain first)
- Direction indicator (↗/↘) is more prominent than numeric value
- "What is a correlation?" disclaimer always accessible via header info icon
- Filter tabs group insights by metric/topic; they do not change analytics tiers
- Existing insights for inactive tags remain visible and receive a neutral "Tag inactive" marker
- Each card has progressive disclosure: statement/context first, expanded details on demand
- Insight metadata must interpolate both `sample_n` and its time window. If the API payload does not
  provide `time_window_days`, cards fall back to the 90-day insight context rather than rendering a
  placeholder token.
- M3.6 insight maturity comes from the API-level `insight_maturity` object; frontend components must not recompute the phase from entry count.
- Default insight cards show `InsightMaturityBadge` instead of raw confidence or p-values; statistical details stay in expanded/detail contexts.
- Empty and locked states explain the current maturity phase instead of using a generic unavailable state.
- Phase milestone cards are explicit-dismiss only and persist in `reached_milestone_keys`; they are not toasts and never auto-dismiss.
- The "Symptoms" filter recognises both current `metric` naming and future symptom insight payloads
  (`insight_type`, `subject_type`, payload/flag kind) so symptom cards can be blended into the feed
  without another route.
- The descriptive `SymptomAnalyticsSection` may be toggled via `cc_insights_symptoms`. It renders a
  neutral symptom-history heatmap below the feed and is hidden in `collecting`; it does not compute
  correlations, lift, p-values, diagnoses or recommendations in the frontend.
- M7 symptom/tag and tag/tag co-occurrence matrices are advanced data tables. Desktop may use
  vertical column labels; mobile must use compact, readable labels and controlled horizontal
  scrolling so headers do not overlap cells.
- Matrix, raw values, sample sizes, confidence, filters, and card detail charts remain reachable through drilldowns. Decluttering must never remove data depth.

---

### Screen 4: Trends (`/trends`)

**M5 Streamline:** `Compare` is the default tab. It shows Mood/Energy/Stress lines above tag and symptom heatmap rows on one shared daily time axis. `Activities` is no longer a default tab; its tag-frequency function is represented by tag rows in Compare.

**Purpose:** Long-term visualisations — mood timeline, tag frequency, work context patterns.

> **ADR-0017 note:** "History", "Calendar", and "Entry list" views are **not separate screens** — they are tabs or secondary sheet overlays within `/trends`. The Entry Detail view (tap on a past entry) opens as a secondary sheet (read-only overlay), not a new route.

**Layout (tab-based):**

```
[Compare] [Health] [Habits]

Time range: [7D] [30D] [90D] [1Y]

┌──────────────────────────────┐
│  Mood over time              │
│  ╭─╮  ╭╮                    │
│ ╭╯ ╰──╯╰╮ ╭─────            │  ← Custom SVG line chart
│─╯        ╰╯                  │
│  Apr          May            │
└──────────────────────────────┘

┌──────────────────────────────┐
│  Work Context                │
│  Home office  ████████ 12d   │
│  Office       █████     7d   │
└──────────────────────────────┘
```

**Rules:**

- Calendar and tag heatmaps use the **theme-owned single-hue neutral scale** (`--color-heatmap-*`); divergent symptom/mood scales follow the **theme-agnostic rule** in [ADR-0035](adr/0035-temporal-correspondence-pattern.md) — never a red/green pair, never hardcoded hues
- No "best day" comparisons or ranking language
- Export button (CSV/JSON) in header — for doctor visits and power users
- Charts are tappable: tap on data point shows tooltip with day details
- Entry History: tap on any data point or calendar cell → secondary sheet overlay with single past entry (read-only)
- Mood charts expose `Raw | Smoothed` for 30D and longer ranges; smoothing is a client-side 7-day SMA persisted in `cc_trend_smooth`.
- Compare uses one canonical `dates[]` axis and shared layout tokens (`labelWidth`, `dayWidth`,
  `dayGap`) for `MetricTimeseries` and `ComparisonHeatmap`. The same ISO date must resolve to the
  same X-position in both the SVG trendline and heatmap rows.
- The 1Y range uses 365 daily timeseries points. Monthly buckets are not allowed in Compare because
  they cannot align exactly with daily heatmap cells.
- Tag and symptom context layers are independently toggleable and persisted in
  `cc_trend_compare_layers`.
- **Compare render mode (M3.8, see [ADR-0035](adr/0035-temporal-correspondence-pattern.md)):** A `Lines | Strips` toggle switches the metric block between line chart and a **Unified-Strip view** (Mood/Energy/Stress rendered as horizontal divergent strips above the tag/symptom heatmap rows). Strip mode shares the canonical `dates[]` axis with all heatmap rows for exact column correspondence and is the recommended mode for ≥30D ranges on mobile. Mode is persisted in `cc_trend_compare_mode`.
- **Dynamic sorting (M3.8):** In Strip mode, tag/symptom rows may be sorted by `frequency`, `recent activity`, `correlation strength` (phase-gated `provisional`+), or `pinned`. Sort key is persisted in `cc_trend_compare_sort`; user-pinned rows in `cc_trend_compare_pins`.
- **Timeline cursor (M3.8):** A single shared cursor synchronises hover/focus across the metric block and all heatmap rows. Keyboard navigation (`←/→`) moves the cursor by one day; `Shift+←/→` jumps by one week.
- **Event markers (M3.8):** Phase transitions, symptom onsets, and habit-goal changes appear as neutral vertical markers across all rows. Marker colour comes from `--color-event-marker-*` tokens and must respect the theme-agnostic colour rule.
- Symptom heatmap is neutral occurrence/intensity visualization only. It does not introduce co-occurrence, medical interpretation, correlation recommendations, or a new analytics engine.
- Mobile uses one controlled horizontal timeline scroller with sticky row labels and compact layer controls. Desktop uses a wider analysis canvas, sticky controls, and may keep an entry-detail panel open beside the chart.
- Health tab may show a cycle-day strip when entries contain `cycle_day`; it must not infer phases or provide medical interpretation.
- Habits tab shows goal-based adherence for `build` / `reduce` habit tags, with a 7/14/28/90 day window selector.
- Habit detail reuses the neutral tag heatmap and may show a correlation contribution from existing insights; insufficient-data copy is target-aware (heatmap remains visible); no streak counters, badges, points, rewards or urgency framing.

---

### Screen 5: Settings (`/settings`)

**Purpose:** Profile, tag/symptom management, privacy, export, analytics toggle, developer mode.

**Layout:**

```
TRACKING
→ Manage tags
→ Manage symptoms
→ Reminders

ANALYSIS
→ Analytics enabled  [✓]
→ Explore insights

PRIVACY & DATA
→ Export all current data  (ZIP: JSON/CSV; photo section remains empty until M13)
→ Delete account

APPEARANCE
→ Dark / Light / System
→ Language: EN / DE

DEVELOPER  ← only visible after unlock (7× tap on version string)
→ Developer mode  [OFF]
→ Force visualizations  [OFF]  ← only visible when Developer mode is ON
→ Insight phase / onboarding / entry-count mocks
```

**Developer Mode rules** (extends [ADR-0015](adr/0015-developer-view-version-identifikation.md), see [ADR-0019](adr/0019-dev-mode-settings-toggle.md)):

- Hidden behind 7× tap on version string in Settings footer
- Toggle writes `dev_mode_enabled` to LocalStorage
- When enabled: `DEV_VIEW_ENABLED` flag activates `/dev` route link in Settings
- **"Force visualizations" sub-toggle** is only visible when `dev_mode_enabled === true`
- `devForceVisualizations` is a `derived` store from `devModeEnabled` — **not** gated by `import.meta.env.DEV` (available to selfhosters in production, see Issue #183)
- Deactivating Developer mode resets `dev_force_viz` and all in-memory `devPhase` overrides
- `devPhase` overrides Insight maturity, onboarding completion, and mock entry count only in the local session
- Onboarding preview opens `/onboarding?preview=1` in a modal and must not write onboarding completion
- Does not count as a user-facing screen — it is a diagnostic tool

**Tag lifecycle rules** (Issue #173):

- Tag Settings must load `GET /api/v1/tags?include_hidden=true` so inactive tags remain reactivatable.
- Active and inactive tags are grouped separately with neutral copy.
- Hidden tags do not appear in new Entry Tag Picker flows.
- Historical entry-tag relations are retained; analytics and heatmap calculations skip hidden tags for new calculations.
- Existing insights that point to inactive tags are not deleted; they are marked as inactive in the UI.
- Habit configuration lives in Tag Settings: `none | build | reduce` plus a weekly target from 1 to 7. `none` clears the target.

---

### Secondary Sheets & Overlays

| Sheet                 | Trigger                         | Content                                   |
| --------------------- | ------------------------------- | ----------------------------------------- |
| **Tag Picker (full)** | "+ More" in entry               | Full tag category view with inline create |
| **Symptom Checker**   | Optional in entry               | Symptom intensity sliders (0–3)           |
| **Insight Detail**    | "Show details" on insight card  | Dual-axis chart + lag selector            |
| **Onboarding Flow**   | First launch / M4               | Guided tag setup, custom tags, summary    |
| **Entry History**     | Date tap / data point in Trends | Single past entry, read-only              |

---

## 6. Insight Card Specification

### 6.1 Anatomy

```
┌──────────────────────────────────────────┐
│ [↗] Exercise & Mood     [████████░░]    │  ← Direction + Title + Confidence bar
│ ──────────────────────────────────────── │
│ "On days with exercise your mood was    │  ← Natural language statement
│  on average 0.8 points higher."         │  (from statement_template engine)
│                                          │
│  Based on 42 entries · 90 days          │  ← sample_n + time window
│  [What does this mean? ⓘ]               │  ← Disclaimer link
│ ──────────────────────────────────────── │
│  [Show details ▼]                        │  ← Progressive disclosure trigger
└──────────────────────────────────────────┘
```

### 6.2 Expanded State — Dual-Axis Chart

```
┌──────────────────────────────────────────┐
│ Exercise & Mood — last 90 days           │
│                                          │
│  +2 ╭╮   ╭──╮       Mood ─────          │
│  +1─╯╰───╯  ╰───╮                       │
│   0              ╰───────               │
│  ● Exercise day  ○ No exercise           │
│                                          │
│  Apr   May                               │
│                                          │
│  Pearson r = +0.52 · p < 0.05           │  ← Shown only in expanded view
│  [Export data]                           │
└──────────────────────────────────────────┘
```

### 6.3 Empty State (< 7 entries)

```
┌──────────────────────────────────────────┐
│  📊 Building your first patterns         │
│                                          │
│  You have logged 4 of the last 7 days.  │
│  CorrelCore needs ~30 entries for       │
│  reliable correlations.                  │
│                                          │
│  Tracking consistency: 4/7 days         │
└──────────────────────────────────────────┘
```

No motivational language. No fire emojis. Neutral, data-based information.

### 6.4 InsightQualityMeter Copy Rules

All copy in `InsightQualityMeter.svelte` must be **descriptive, never imperative**. The following table defines the canonical copy for each stage:

| Entries | Stage           | Correct copy                                                                     |
| ------- | --------------- | -------------------------------------------------------------------------------- |
| 0–3     | Getting started | "Your data is being collected. First patterns become visible around 30 entries." |
| 4–29    | Building data   | "At your current tracking pace: ca. X weeks until first insight."                |
| 4–29    | No recent data  | "No recent entries found. Estimated time to first insight cannot be calculated." |
| 30–89   | Low confidence  | First insight visible — confidence label shown                                   |
| 90+     | Medium / High   | Full insights                                                                    |

**Prohibited patterns:** emoji in progress display, imperative verbs (`Track`, `Log`, `Don't`), urgency language (`speed up`, `falling behind`, `almost there`).

---

## 7. Component Structure (Atomic Design)

```
apps/web/src/
├── lib/
│   ├── components/
│   │   ├── common/          # Shared primitives: Button, IconButton,
│   │   │                    # ScreenHeader, Panel, SegmentedControl,
│   │   │                    # TabBar, BottomSheet, DataState,
│   │   │                    # EmptyState, InlineAlert, Input, Badge
│   │   ├── auth/            # Auth-specific components
│   │   ├── home/            # HomeTodayContext, HomeDailyBrief,
│   │   │                    # HomeWorkContextSummary, HomeWeekdayOverview,
│   │   │                    # FirstWeekInsightBanner, MetricCard (landing)
│   │   ├── insights/        # InsightCard, InsightCardExpanded,
│   │   │                    # InsightFeed, InsightMatrix, CorrelationBadge,
│   │   │                    # DualAxisChart, InsightQualityMeter
│   │   │   └── symptoms/    # SymptomAnalyticsSection
│   │   ├── trends/          # MetricTimeseries, TagHeatmap,
│   │   │                    # ComparisonHeatmap, TrendsComparePanel
│   │   └── entries/         # EntryForm, TagPicker, SymptomChecker
│   ├── api/
│   │   ├── client.ts        # apiFetch + single-flight refresh
│   │   ├── auth.ts          # Auth API calls
│   │   └── insights.ts      # Insights API calls
│   ├── config/
│   │   └── metrics.ts       # Canonical metric definitions incl. invert flag (§4.3)
│   ├── stores/
│   │   ├── auth.ts          # AuthState store
│   │   ├── devMode.ts       # devModeEnabled + devForceVisualizations (ADR-0019)
│   │   └── insights.ts      # InsightStore (latest, all, dismissed IDs)
│   ├── utils/
│   │   └── streak.ts        # Tracking consistency calculation (not streak)
│   ├── data/                # Static data, tag defaults
│   └── i18n/
│       ├── de.json
│       └── en.json
└── routes/
    ├── +layout.svelte       # App shell (nav, auth guard)
    ├── +page.svelte         # Home
    ├── auth/                # Public: login, register, verify-email
    ├── insights/
    │   └── +page.svelte     # Insights feed
    ├── trends/
    │   └── +page.svelte     # Trend visualisations (Compare + Entry History sheet)
    ├── settings/
    │   ├── +page.svelte     # Settings
    │   └── tags/            # Tag management sub-page
    ├── onboarding/          # Guided flow (+page), profile questionnaire, retro batch
    │   ├── +page.svelte     # M4 3-step guided onboarding
    │   ├── profile/         # Optional onboarding profile (M3)
    │   └── retro/           # Retrospective entry batch (M3 cold-start)
    ├── offline/             # PWA navigation fallback (M4)
    ├── dev/                 # Developer view (ADR-0015, ADR-0019)
    └── status/              # Health status page
```

---

## 8. Insights Store

```typescript
// stores/insights.ts
interface InsightStore {
  insights: Insight[]; // All insights from worker
  insightMaturity: InsightMaturity | null; // Backend-owned phase contract
  latest: Insight | null; // For home screen (Sprint 6 implemented)
  loading: boolean;
  error: string | null;
  dismissedIds: string[]; // From user_preferences
}
```

The insights store is best-effort: a load failure must not propagate an error state to unrelated home screen components.

---

## 9. Motion & Animations

- **Duration:** 150–250 ms for standard transitions
- **Easing:** `ease-out` for entrances, `ease-in` for exits
- **Reduced motion:** `@media (prefers-reduced-motion: reduce)` → `transition: none`
- **No layout shifts** caused by animations (CLS budget)

```css
.fade-in {
  animation: fadeIn 200ms ease-out;
}
@media (prefers-reduced-motion: reduce) {
  .fade-in {
    animation: none;
  }
}
```

---

## 10. Accessibility (WCAG 2.2 AA)

- All interactive elements keyboard-navigable
- Mood slider: also operable with +/− buttons (screen reader + motor impairment)
- Colour contrast: ≥ 4.5:1 (normal text), ≥ 3:1 (large text)
- Visible focus outline, never removed
- ARIA labels on all icon-only buttons
- `prefers-reduced-motion`: animations disabled or minimised
- Confidence bar must have `aria-label` with text label (not just visual fill)

---

## 11. Internationalisation (i18n)

- **From day 1:** DE and EN
- No hardcoded strings in template code
- Library: **`svelte-i18n`** (current implementation; a future `paraglide-js` migration needs its own ADR)
- Language switching: update the active `svelte-i18n` locale directly; do not add a parallel custom locale store
- Locale preference persisted via LocalStorage as client-side fallback; sync via `PATCH /api/v1/user/settings { locale: 'de' }` only after the backend preference field exists
- Locale files: `apps/web/src/lib/i18n/de.json` and `en.json`
- Date formats: `Intl.DateTimeFormat` (locale-aware)
- Insight statement templates are locale-keyed — the backend returns a `statement_key`, the frontend resolves the localised string

---

## 12. Authentication

See [ADR-0006](adr/0006-cookie-auth-mit-capacitor-migration.md) for full details.

- **Mechanism:** HttpOnly cookies (`SameSite=Strict`, `Secure` in prod)
- **Auth guard:** Root `+layout.svelte` redirects unauthenticated users to `/auth/login?next=<path>`
- **Route groups:** All authenticated screens live under the implicit `(app)` layout group

| Route                | Purpose            | Public        |
| -------------------- | ------------------ | ------------- |
| `/auth/login`        | Sign in            | ✅            |
| `/auth/register`     | Registration       | ✅            |
| `/auth/verify-email` | Email confirmation | ✅            |
| `/`                  | Home               | 🔒            |
| `/insights`          | Insights feed      | 🔒            |
| `/trends`            | Trend charts       | 🔒            |
| `/settings`          | Settings           | 🔒            |
| `/dev`               | Developer view     | 🔒 + dev flag |

---

## 13. Key Design Questions Checklist

Every new component or screen decision must be checked against:

**Product level**

- [ ] Is this completable in 60 seconds (entry flow) or < 3 scrolls (insights)?
- [ ] Does this component add truth or just mood?
- [ ] Does the user understand correlation ≠ causation here?
- [ ] Does this screen work with zero data (empty state defined)?

**Technical level**

- [ ] Stateless atom or store-consuming organism?
- [ ] Uses an approved shared primitive from `frontend/UI_COMPONENT_SYSTEM.md`?
- [ ] Custom SVG chart or library? (library needs ADR)
- [ ] Renders without horizontal scroll at 375 px?
- [ ] All four component states defined (loading/error/empty/offline)?
- [ ] All strings in locale file?
- [ ] Metric uses correct `invert` flag from `src/lib/config/metrics.ts` (§4.3)?

**No-gamification gate**

- [ ] No streak counter?
- [ ] No badge or reward animation?
- [ ] Heatmap uses neutral blue-tone scale?
- [ ] Notification copy is neutral?
- [ ] InsightQualityMeter copy is descriptive, not imperative (§6.4)?

## 12. M3.5 Closeout Notes

Sprint 9 records the QA handoff in [`quality/M3_5_VISUAL_QA.md`](quality/M3_5_VISUAL_QA.md). The implemented M3.5 screen model is:

- Home: fixed Today Strip, configurable compact blocks (`/settings/home`), primary CTA when today is open.
- Entry: bottom sheet/page mode with sectioned form, neutral work-context hint, auto-save status, and Day Delta.
- Insights: single Stage Header, filterable insight feed, disclaimer access, progressive detail expansion, matrix drilldown, and inactive-tag markers.
- Trends: Compare / Health / Habits tabs, unified ranges, custom SVG charts, tag/symptom context rows, and Entry History sheet overlay.
- Settings: Tracking / Analysis / Privacy & Data / Appearance (incl. **Home layout** at `/settings/home`) / Developer sections, language control, theme toggle, Dev Mode, Force Visualizations, phase mocks, and Tag Settings active/inactive lifecycle.
- PWA: Home install banner is dismissible via `cc_pwa_dismissed`; `/offline` is the navigation fallback; service worker skips `/api/*`.

Rendered browser QA is documented as pending outside this NAS/UNC agent environment because the local pnpm install/test path cannot create symlinks on the network share. Do not treat that tooling limitation as a frontend design exception; run the rendered viewport/theme matrix from a local clone or CI environment before release tagging.
