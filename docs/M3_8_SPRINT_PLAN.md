# M3.8 Sprint Plan — Temporal Correspondence Pattern

Last updated: 2026-05-30

M3.8 is a focused frontend visualisation milestone that implements the
three-layer Temporal Correspondence Pattern decided in
[ADR-0035](adr/0035-temporal-correspondence-pattern.md). It addresses user
feedback that the existing shared-axis Compare view does not yet make the
relationship between continuous trends (Mood/Energy/Stress) and discrete
events (tags, symptoms) cognitively accessible.

**Prerequisite:** M3.7 (Color System Hardening) must be merged before M3.8
begins. ADR-0035 explicitly depends on the divergent-scale token contract
introduced in M3.7. The first sub-sprint of M3.8 (Sprint 0) extends that
contract with two new theme tokens.

**Sprint discipline:** Per Space convention, the three layers of ADR-0035 ship
**sequentially**. No parallel work on chart components across sub-sprints —
each sub-sprint must be merged and stabilised before the next begins. This is
deliberately strict to prevent the chart-component conflict pattern that
emerged during M3.5/M3.6.

---

## Goal

Make temporal correspondence between continuous metrics and discrete
tags/symptoms directly perceivable in the `/trends` and `/insights` routes.
Deliverables span documentation, theme contract, chart library adoption, and
three sequential visualisation layers:

- ADR-0035 filed and merged ✅ (this sprint, Sprint 0)
- Theme contract extended with `--color-divergent-{neg,pos,mid}` tokens
- D-002 superseded language reflected in DESIGN_DOCUMENT §7 and §1.4
- FRONTEND.md §Screen 4 updated with Lines/Strips dual-mode description
- Layer 1: synchronised cursor + pinned event markers
- Layer 2: LayerChart adoption + Unified-Strip render mode + dynamic sorting
- Layer 3: Event-aligned small-multiples sheet (phase-gated `provisional`+)

---

## Sources of Truth

- [ADR-0035](adr/0035-temporal-correspondence-pattern.md) — temporal correspondence pattern
- [ADR-0017](adr/0017-frontend-screen-architecture.md) — secondary-sheet conventions
- [ADR-0021](adr/0021-insight-maturity-phases.md) — phase gating
- [`FRONTEND.md`](FRONTEND.md) §Screen 4 — Trends layout
- [`COLOR_SCHEME_CONCEPT.md`](frontend/COLOR_SCHEME_CONCEPT.md) — theme tokens
- `apps/web/src/lib/components/trends/` — existing chart components

---

## Sprint 0 — ADR Documentation & Theme Contract Extension

**Goal:** All architectural decisions are recorded and the theme contract is
ready to host the divergent-scale tokens required by Layers 2 and 3.

**Status:** in progress (this PR)

### Deliverables

- [ ] `docs/adr/0035-temporal-correspondence-pattern.md` — merged
- [ ] `docs/adr/README.md` index updated with ADR-0035
- [ ] `docs/DESIGN_DOCUMENT.md` §7 D-002 row updated: status → "Partially
      superseded by ADR-0035"
- [ ] `docs/DESIGN_DOCUMENT.md` §1.4 No-Gamification — divergent-scale rule
      restated in theme-agnostic form (no hue names)
- [ ] `docs/FRONTEND.md` §Screen 4 updated to reference the Lines/Strips
      dual-mode (description only, implementation in Sprints 1–3)
- [ ] `docs/frontend/COLOR_SCHEME_CONCEPT.md` — new subsection
      "Divergent Scales (theme contract)" describing the three required tokens
- [ ] `apps/web/src/app.css` — `--color-divergent-neg`,
      `--color-divergent-pos`, `--color-divergent-mid` added to both dark and
      light mode blocks (current violet/dark theme values chosen by theme
      authors; structural rule defined in ADR-0035)

### Exit criteria

- [ ] ADR-0035 present in `docs/adr/` and indexed in `docs/adr/README.md`
- [ ] DESIGN_DOCUMENT and FRONTEND.md reflect the partial supersession
- [ ] Theme tokens present in `app.css` and pass `pnpm check:contrast`
- [ ] No code changes outside docs and theme tokens in this sprint

---

## Sprint 1 — Layer 1: Synchronised Cursor + Event Markers

**Goal:** A user dragging or tapping on either the line chart or any heatmap
row sees a synchronised vertical cursor across both, with a floating detail
card. Optional pinned event markers on the metric lines highlight up to three
user-selected tags or symptoms.

**Prerequisite:** Sprint 0 merged.

### Scope

- New module `apps/web/src/lib/stores/timelineCursor.ts` — single source of
  truth for cursor state `{ x: number | null, date: string | null, source: 'lines' | 'heatmap' | 'keyboard' }`.
- `MetricTimeseries.svelte` extended to publish and subscribe to the store.
- `ComparisonHeatmap.svelte` extended likewise; columns highlight on hover or
  cursor presence.
- New component `TrendsCursorOverlay.svelte` — the vertical line + floating
  card, positioned by the active cursor state.
- New component `EventMarkerLayer.svelte` — overlays glyphs on the metric
  lines for the user's pinned event subjects (max 3, persisted in
  `cc_trend_compare_pins`).
- Compare-tab UI: a "Pin tag/symptom for marker" affordance, hard-limited to 3.

### Out of scope (deferred)

- Strip render mode (Sprint 2)
- Event-aligned panels (Sprint 3)
- New library dependencies (Sprint 2)

### Exit criteria

- [ ] Tap, drag, and arrow-key navigation on `/trends` Compare view move a
      synchronised cursor across the line chart and all heatmap rows
- [ ] Floating detail card shows date + Mood/Energy/Stress + active
      tags/symptoms for the cursor date
- [ ] Up to 3 pinned subjects render as markers on the metric lines
- [ ] All existing Playwright snapshot tests for `/trends` still pass; new
      tests added for cursor interaction
- [ ] Mobile (375 px): touch-drag works smoothly; cursor does not block
      underlying tap targets
- [ ] A11y: cursor is keyboard-controllable; floating card is announced
      correctly by screen readers
- [ ] No change to JS bundle > 5 KB gz (pure SVG + store, no new dependencies)

---

## Sprint 2 — Layer 2: LayerChart Adoption + Unified-Strip Mode

**Goal:** Adopt LayerChart as the chart library for analytical deep views.
Add a render-mode toggle `Lines | Strips` to the Compare view. Add dynamic
sort modes for heatmap rows.

**Prerequisite:** Sprint 1 merged.

### Scope

- Add `layerchart` dependency to `apps/web/package.json`. Validate marginal
  bundle cost against the 80 KB gz budget defined in ADR-0035.
- New module `apps/web/src/lib/charts/adapter/index.ts` — thin wrapper around
  LayerChart imports. All future chart code imports through this module to
  isolate library lock-in.
- New script `pnpm check:bundle:trends` — fails CI if the marginal bundle
  cost for the trends route exceeds 80 KB gz over the M3.7 baseline.
- `MetricTimeseries.svelte` gains a `mode: 'lines' | 'strips'` prop. In Strip
  mode, each metric is rendered as a divergent heatmap row encoding Z-score
  against the user's rolling 30-day baseline mean, using the theme's
  `--color-divergent-{neg,pos}` tokens.
- New util `apps/web/src/lib/utils/baseline.ts` — rolling mean + standard
  deviation computation for the Z-score input. Pure functions, unit-tested.
- Compare-tab UI: a `Lines | Strips` segmented control persisted in
  `cc_trend_compare_mode`. Auto-default to `strips` if active tag count > 12
  (one-time hint, dismissable).
- Heatmap row sort modes: `alphabetical` (default), `correlation-to-mood`,
  `correlation-to-energy`, `correlation-to-stress`. Sort applied
  client-side from existing pointbiserial correlation results in the trends
  payload. Persisted in `cc_trend_compare_sort`.

### Out of scope (deferred)

- Event-aligned panels (Sprint 3)
- Lag-correlation visualisations (not in M3.8 — future M7 work)

### Exit criteria

- [ ] LayerChart installed and only used through the adapter module
- [ ] `pnpm check:bundle:trends` passes; marginal cost documented in the PR
- [ ] Compare view offers `Lines | Strips` toggle, default `lines`
- [ ] Strip mode: Mood/Energy/Stress strips align pixel-exactly with tag and
      symptom rows on the same date columns
- [ ] Divergent colour scale uses only theme tokens; no hue hardcoded
- [ ] Sort-by-correlation produces correct ordering against existing
      pointbiserial test fixtures
- [ ] All M3.7 contrast and `check:contrast` gates still pass
- [ ] Playwright snapshot tests cover both modes on dark and light theme
- [ ] Mobile (375 px): both modes scrollable under one horizontal scroller
      with sticky labels; no horizontal jitter when switching modes

---

## Sprint 3 — Layer 3: Event-Aligned Small Multiples

**Goal:** Tapping on a tag, symptom, or pinned marker opens a secondary sheet
(per ADR-0017) with small multiples of the metric trends, each centred on every
occurrence of that event.

**Prerequisite:** Sprint 2 merged.

### Scope

- New component `EventAlignedPanelsSheet.svelte` in
  `apps/web/src/lib/components/trends/`. Opens as a secondary sheet (no new
  route).
- Per occurrence of the selected event, render a small multiple of
  Mood/Energy/Stress on a relative time axis (`-7d … +7d`, configurable to
  `±14d`). Use the LayerChart adapter from Sprint 2.
- Overlay a **median trajectory** across all occurrences, with a band showing
  the interquartile range.
- Phase gating: visible only when insight phase ≥ `provisional`. In `early_patterns`
  the entry point is disabled with the standard maturity tooltip
  (ADR-0021).
- Methodology disclaimer modal: extends `CorrelationDisclaimer` patterns
  (per `SYMPTOM_VISUALIZATION.md`). Copy emphasises that visual co-occurrence
  is not causal.
- Empty/sparse-state handling: requires ≥ 3 occurrences of the selected event
  in the visible window to render the median band; below that, only individual
  small multiples render and a "Need more data" hint is shown.

### Out of scope (deferred)

- Statistical confidence per small multiple (M7 — beyond this milestone)
- Backend changes (Layer 3 is purely a frontend view of existing entry data)

### Exit criteria

- [ ] Tap on tag row, symptom row, or pinned marker opens the
      `EventAlignedPanelsSheet`
- [ ] All occurrences of the event within the current trends range are rendered
      as small multiples
- [ ] Median + IQR band correctly computed against unit-test fixtures
- [ ] Sheet is phase-gated; methodology disclaimer reachable from sheet header
- [ ] Empty-state and sparse-state handling verified
- [ ] All existing tests pass; new tests for sheet and median computation
- [ ] Mobile: sheet uses bottom-sheet semantics per ADR-0017; desktop uses
      side panel
- [ ] A11y: sheet trap-focus, escape-to-close, screen-reader landmarks correct

---

## Cross-cutting Quality Gates

These apply to all three sprints, not just the final one:

- **Library hygiene** — new dependencies documented in PR description; the
  LayerChart adapter (Sprint 2) is the **only** module that imports
  `layerchart` directly. Direct imports elsewhere fail CI via a new ESLint
  rule.
- **Bundle budget** — `pnpm check:bundle:trends` runs in CI from Sprint 2
  onward and blocks merge if marginal cost > 80 KB gz.
- **Theme conformance** — no hue hardcoded in any chart component. Linting
  via the existing `no-hardcoded-color` rule from M3.7.
- **A11y** — every new interactive primitive has keyboard equivalents and
  ARIA semantics. Playwright A11y snapshots extended per sprint.
- **No-Gamification** — divergent scales follow the structural rule in
  ADR-0035; rejected hue pairs (red↔green and ±20°) are blocked at lint level
  via a new ESLint rule added in Sprint 2.

---

## Risks and Mitigations

| Risk                                              | Likelihood | Impact                                   | Mitigation                                                                                              |
| ------------------------------------------------- | ---------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| LayerChart marginal cost > 80 KB gz               | Low        | High (would require revisiting ADR-0035) | Run bundle measurement spike in Sprint 2 Day 1; if over budget, reduce to uPlot + custom heatmap        |
| Strip mode visually overwhelming for new users    | Medium     | Medium                                   | Keep `lines` as default; show one-time hint for `strips` only when >12 tags                             |
| Event-aligned median misleading on sparse data    | Medium     | High (insight quality risk)              | Require ≥ 3 occurrences for median; explicit disclaimer; phase gating ≥ `provisional`                   |
| Synchronised cursor performance on low-end mobile | Low        | Medium                                   | Throttle cursor updates to rAF; benchmark on Moto G4 baseline device                                    |
| Theme migration later breaks divergent scale      | Low        | Medium                                   | Tokens are structural; any future theme must define conformant `--color-divergent-{neg,pos}` to pass CI |

---

## Out of Scope for M3.8

- Backend changes to analytics (no new statistical methods in this milestone)
- Lag-correlation visualisations — deferred to M7 Insights v2
- PNG export of new charts — covered in existing M2 backlog
- Onboarding tour updates for the new modes — deferred to M4 Quick Wins
