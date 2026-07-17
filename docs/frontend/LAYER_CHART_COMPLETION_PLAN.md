# LayerChart Adapter — Completion Plan

Status: **Deferred** after D-L1 spike (2026-07-16)  
Last updated: 2026-07-16  
Spike: [`LAYER_CHART_SPIKE_2026-07-16.md`](LAYER_CHART_SPIKE_2026-07-16.md)  
Related: [ADR-0035](../adr/0035-temporal-correspondence-pattern.md), `apps/web/src/lib/charts/adapter/index.ts`

---

## Decision

**Do not add `layerchart` now.** Custom SVG remains production. LayerChart 2.0 is
Svelte 5–compatible; revisit when Trends Compare lasagna (or equivalent) is
scheduled and the gzip chunk is measured ≤ 80 KB.

---

## When to reopen

1. Product accepts a Trends Compare multi-row / lasagna milestone item.
2. Spike installs `layerchart@^2`, implements `lazyLoadLayerChart()`, measures CI chunk size.
3. Gate behind maturity/dev flag with SVG fallback.

Until then: keep the adapter stub; do not invent parallel React chart stacks.
