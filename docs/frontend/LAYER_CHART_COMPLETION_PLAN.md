# LayerChart Adapter — Completion Plan

Status: **Planned** (custom SVG path is production; LayerChart loader is a stub)  
Last updated: 2026-07-16  
Related: [ADR-0035](../adr/0035-temporal-correspondence-pattern.md), `apps/web/src/lib/charts/adapter/index.ts`

---

## Current state

| Piece | Status |
| ----- | ------ |
| Custom SVG charts (mood series, heatmaps, strips) | Production |
| `StripCellMapper` / divergent tokens | Shipped |
| `lazyLoadLayerChart()` | Always returns `null` |
| `layerchart` dependency | **Not** in `apps/web/package.json` |
| Bundle budget (ADR-0035 §11) | 80 KB gz marginal hard cap |

Temporal correspondence UX (explore aligned events, small multiples gate) already uses the custom path. LayerChart was reserved for denser multi-series / lasagna layouts that custom SVG does not scale to well.

---

## Goal

Introduce LayerChart **only** behind the adapter, with a measured bundle impact and a graceful fallback to custom SVG when the chunk fails to load or the budget is exceeded.

---

## Decisions required before implementation

| ID | Decision | Options | Recommendation |
| -- | -------- | ------- | -------------- |
| D-L1 | Is LayerChart still the library? | LayerChart vs keep custom-only vs alternate | Confirm LayerChart against current Svelte major; if abandoned/incompatible, **close adapter as permanent custom-SVG** and update ADR-0035 |
| D-L2 | First consumer screen | Trends Compare lasagna vs Insights matrix polish | **Trends Compare** (highest ADR-0035 value) |
| D-L3 | Feature flag | Always when loaded vs Settings/dev flag | Dev flag or maturity-gate until bundle proven |
| D-L4 | Failure mode | Invisible fallback vs “enhanced charts unavailable” note | Silent fallback to custom SVG |

---

## Work packages

### WP1 — Dependency & adapter flip

1. Add `layerchart` (pin version) to `@correlcore/web`.
2. Implement `lazyLoadLayerChart()` as dynamic `import('layerchart')` with try/catch → `null`.
3. Export a narrow typed surface from the adapter (no re-export of full library elsewhere).
4. CI: fail if chart chunk gzip size > 80 KB (or document waiver).

### WP2 — First chart port

1. Port one ADR-0035 consumer (recommended: lasagna / multi-row strip on Trends Compare).
2. Keep custom SVG as default until flag/gate enables LayerChart branch.
3. Visual QA: 375 / 768 / 1280, light + dark, reduced motion.

### WP3 — Cleanup

1. Remove permanent-null tests; add load-success + fallback tests.
2. Update ADR-0035 “implementation notes” with chosen version and measured size.
3. If D-L1 chooses custom-only: delete `lazyLoadLayerChart`, mark ADR section superseded.

---

## Acceptance criteria

- [ ] D-L1 decided and recorded in ADR-0035 or a short ADR amendment
- [ ] Adapter is the **only** import site for the library
- [ ] Bundle budget measured in CI or release checklist
- [ ] At least one user-visible chart uses LayerChart behind a gate with SVG fallback
- [ ] No regression on existing custom SVG screens when LayerChart fails to load

---

## Non-goals

- Replacing every custom SVG chart in one milestone
- Shared chart package under `packages/` (deferred until second GUI needs it)
