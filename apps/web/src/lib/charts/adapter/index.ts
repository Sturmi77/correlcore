/**
 * Chart Adapter — M3.8 Sprint 2 (ADR-0035)
 *
 * This module is the **only** place in the application that is allowed
 * to import from the external chart library (LayerChart, per ADR-0035).
 * Every consumer of advanced chart primitives MUST go through this
 * adapter so we can:
 *
 * 1. Keep the marginal bundle budget bounded (80 KB gz, ADR-0035 §11).
 * 2. Swap the underlying library without rewriting call sites.
 * 3. Enforce CorrelCore's theme-token rules (no hue hardcoded).
 *
 * The adapter currently exposes:
 *
 * - StripCellMapper       Pure helper that resolves a metric value to
 *                        a divergent token + opacity, theme-agnostic.
 * - resolveDivergentToken Token resolver used by the custom-SVG
 *                        Unified-Strip chart in Sprint 2.
 * - lazyLoadLayerChart    Async loader stub (returns null until LayerChart
 *                        is adopted). Completion plan:
 *                        docs/frontend/LAYER_CHART_COMPLETION_PLAN.md
 *
 * Hard rule: no chart-library symbol may be re-exported from anywhere
 * outside this folder. See docs/adr/0035-temporal-correspondence-pattern.md.
 */

export type DivergentSign = 'neg' | 'mid' | 'pos';

export interface DivergentEncoding {
  /** Resolved CSS variable reference, ready to drop into a style attribute. */
  color: string;
  /** Opacity 0..1 derived from |normalised value|. Mid = 0. */
  opacity: number;
  /** Discrete bucket for ARIA / data-attribute serialisation. */
  sign: DivergentSign;
}

/**
 * Map a normalised value in [-1, +1] to a divergent encoding using
 * the theme tokens defined in app.css.
 *
 * - value <= -0.0625  → --color-divergent-neg with opacity from |value|
 * - value >= +0.0625  → --color-divergent-pos with opacity from |value|
 * - otherwise          → --color-divergent-mid, opacity 0
 *
 * The dead band around zero keeps the strip visually quiet for
 * near-neutral days and avoids flicker on noisy inputs.
 */
export function resolveDivergentToken(normalised: number): DivergentEncoding {
  if (!Number.isFinite(normalised)) {
    return { color: 'var(--color-divergent-mid)', opacity: 0, sign: 'mid' };
  }
  const clamped = Math.max(-1, Math.min(1, normalised));
  const absVal = Math.abs(clamped);
  if (absVal < 0.0625) {
    return { color: 'var(--color-divergent-mid)', opacity: 0, sign: 'mid' };
  }
  const sign: DivergentSign = clamped < 0 ? 'neg' : 'pos';
  const color = sign === 'neg' ? 'var(--color-divergent-neg)' : 'var(--color-divergent-pos)';
  // Map |value| ∈ [0.0625, 1] → opacity ∈ [0.25, 1] (perceptually friendlier).
  const opacity = 0.25 + 0.75 * Math.min(1, (absVal - 0.0625) / 0.9375);
  return { color, opacity, sign };
}

/**
 * Strip cell mapper used by UnifiedStripChart (Sprint 2). Encapsulates
 * the per-metric normalisation so the chart component never touches
 * raw value math.
 */
export interface StripCellMapperConfig {
  /** Metric mid point (e.g. 3 on a 1..5 mood scale). */
  midpoint: number;
  /** Full range (e.g. 4 = 5 - 1). */
  range: number;
}

export class StripCellMapper {
  constructor(private readonly config: StripCellMapperConfig) {}

  /** Returns a divergent encoding for a raw metric value. */
  encode(value: number | null | undefined): DivergentEncoding {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return { color: 'var(--color-divergent-mid)', opacity: 0, sign: 'mid' };
    }
    const normalised = (value - this.config.midpoint) / (this.config.range / 2);
    return resolveDivergentToken(normalised);
  }
}

/**
 * Async loader for the external chart library. Returns null while the
 * dependency is not yet installed in package.json — consumers must
 * gracefully fall back to the custom-SVG implementation.
 *
 * When LayerChart is added (Sprint 2 follow-up commit), this becomes:
 *
 *   const mod = await import('layerchart');
 *   return mod;
 *
 * The async signature is kept so that flipping the body to the real
 * dynamic import is a one-line change and code-splitting is honoured
 * from the start (bundle-budget hard rule, ADR-0035 §11).
 */
export async function lazyLoadLayerChart(): Promise<unknown | null> {
  // Intentional no-op until the dependency lands. Components must check
  // for null and fall back to the custom-SVG renderer.
  return null;
}

export const adapterMetadata = {
  /** Reported in dev mode to confirm bundle isolation. */
  name: 'correlcore-chart-adapter',
  /** Bumped whenever the underlying library or contract changes. */
  version: '0.1.0',
  /** Hard marginal bundle budget for the chart library (gz, ADR-0035). */
  bundleBudgetGzKb: 80,
} as const;
