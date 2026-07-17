# LayerChart D-L1 Spike — 2026-07-16

Decision record for whether to adopt LayerChart behind
`apps/web/src/lib/charts/adapter/index.ts`.

## Inputs

| Fact | Finding |
| ---- | ------- |
| App stack | Svelte 5 (`^5.0.0`), SvelteKit 2, Tailwind 4 |
| Current charts | Custom SVG only; production Trends/Insights use this path |
| Adapter | `lazyLoadLayerChart()` returns `null`; **no** consumers call it |
| Library | **LayerChart 2.0.0** (2026-07) — Svelte 5 runes/snippets, Tailwind optional |
| ADR-0035 budget | ≤ 80 KB gz marginal |

## Compatibility

LayerChart **v2 is Svelte 5–native** and no longer requires Tailwind. That removes
the previous blocker (v1 was Svelte 4–era). A fresh adoption should target
`layerchart@^2`, not 1.x.

## Bundle risk

ADR-0035 estimated ≈ 55–65 KB gz for the intended subset. This spike did **not**
install the package or measure a production Vite chunk. Until a measured
import of the exact components for Trends Compare is under 80 KB gz in CI, the
budget remains an assumption.

## Product need

No shipping screen is blocked on LayerChart today. Temporal correspondence
(explore events, custom strips) already works on custom SVG. The first valuable
consumer would be denser lasagna / multi-row Compare views — not yet scheduled.

## Decision (D-L1)

**Defer adoption.** Keep custom SVG as the production renderer. Keep the adapter
stub and completion plan, but do **not** add `layerchart` to `package.json` in
this change set.

Revisit when:

1. Trends Compare lasagna (or equivalent) is an accepted milestone item, and  
2. A measured `lazyLoadLayerChart()` chunk is ≤ 80 KB gz in CI.

If LayerChart is rejected later for budget or API churn, close the adapter and
amend ADR-0035 to “custom SVG only”.

## Related

- [`LAYER_CHART_COMPLETION_PLAN.md`](LAYER_CHART_COMPLETION_PLAN.md)
- [ADR-0035](../adr/0035-temporal-correspondence-pattern.md)
