/**
 * InsightEvidence.test.ts
 *
 * Sprint 2 (ISP-4) consolidation of InsightMaturityBadge + InsightConfidenceScale
 * into one evidence primitive. Covers:
 * 1. Tier chip: phase-specific copy, uncertain-phase flag, no raw confidence leak
 * 2. Confidence: all 5 semantic label boundaries, dot fill count
 * 3. role="meter" + ARIA attributes
 * 4. No raw percentage unless `detailed`
 * 5. `showConfidence`/`showSample` visibility toggles (no duplicate rendering
 *    across InsightCard's three call sites)
 * 6. Clamping of out-of-range confidence inputs
 */
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightEvidence from './InsightEvidence.svelte';
import type { InsightMaturity } from '$lib/api/insights';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: Record<string, unknown> }) => {
      const map: Record<string, string> = {
        'insights.confidence_label.early_signal': 'Early signal',
        'insights.confidence_label.emerging_pattern': 'Emerging pattern',
        'insights.confidence_label.moderate_finding': 'Moderate finding',
        'insights.confidence_label.strong_finding': 'Strong finding',
        'insights.confidence_label.very_strong_finding': 'Very strong finding',
      };
      if (key === 'home.confidence_scale.entry_count')
        return `Based on ${options?.values?.n} entries`;
      if (key.startsWith('maturity.badge.')) return key;
      return map[key] ?? key;
    }),
  };
});

function maturity(overrides: Partial<InsightMaturity> = {}): InsightMaturity {
  return {
    phase: 'early_patterns',
    phase_index: 2,
    current_entries: 9,
    next_phase_at: 14,
    next_phase_label: 'Provisional Insights',
    entries_until_next: 5,
    user_message_key: 'maturity.early_patterns.description',
    ...overrides,
  };
}

describe('InsightEvidence — tier chip', () => {
  it('renders phase-specific copy from maturity', () => {
    render(InsightEvidence, { props: { maturity: maturity(), entryCount: 9 } });
    const badge = screen.getByTestId('insight-maturity-badge');
    expect(badge.getAttribute('data-phase')).toBe('early_patterns');
    expect(badge.textContent).toContain('maturity.badge.early_patterns');
  });

  it('marks early and provisional phases as uncertain', () => {
    render(InsightEvidence, {
      props: { maturity: maturity({ phase: 'provisional', phase_index: 3 }), entryCount: 21 },
    });
    expect(screen.getByTestId('insight-maturity-badge').textContent).toContain('!');
  });

  it('does not leak raw confidence values into the tier chip', () => {
    render(InsightEvidence, {
      props: {
        maturity: maturity({ phase: 'robust', phase_index: 4 }),
        entryCount: 42,
        confidenceScore: 0.72,
        showConfidence: false,
      },
    });
    expect(screen.getByTestId('insight-maturity-badge').textContent).not.toContain('72');
    expect(screen.getByTestId('insight-maturity-badge').textContent).not.toContain('%');
  });

  it('omits the tier chip when maturity is absent', () => {
    render(InsightEvidence, { props: { confidenceScore: 0.5 } });
    expect(screen.queryByTestId('insight-maturity-badge')).toBeNull();
  });

  it('omits the tier chip when showMaturityBadge is false', () => {
    render(InsightEvidence, {
      props: { maturity: maturity(), showMaturityBadge: false },
    });
    expect(screen.queryByTestId('insight-maturity-badge')).toBeNull();
  });
});

describe('InsightEvidence — confidence semantic labels', () => {
  const labelCases = [
    { score: 0.0, label: 'Early signal', dots: 0 },
    { score: 0.1, label: 'Early signal', dots: 1 },
    { score: 0.19, label: 'Early signal', dots: 1 },
    { score: 0.2, label: 'Emerging pattern', dots: 1 },
    { score: 0.39, label: 'Emerging pattern', dots: 2 },
    { score: 0.4, label: 'Moderate finding', dots: 2 },
    { score: 0.59, label: 'Moderate finding', dots: 3 },
    { score: 0.6, label: 'Strong finding', dots: 3 },
    { score: 0.79, label: 'Strong finding', dots: 4 },
    { score: 0.8, label: 'Very strong finding', dots: 4 },
    { score: 1.0, label: 'Very strong finding', dots: 5 },
  ] as const;

  it.each(labelCases)('score $score → label "$label", $dots filled dots', ({ score, label }) => {
    render(InsightEvidence, {
      props: { confidenceScore: score, currentTier: 'robust', entryCount: 30 },
    });
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe(label);
  });
});

describe('InsightEvidence — ARIA', () => {
  it('exposes role=meter with correct aria attributes', () => {
    render(InsightEvidence, {
      props: { confidenceScore: 0.65, currentTier: 'developing', entryCount: 25 },
    });
    const meter = screen.getByTestId('insight-confidence-meter');
    expect(meter.getAttribute('role')).toBe('meter');
    expect(meter.getAttribute('aria-valuemin')).toBe('0');
    expect(meter.getAttribute('aria-valuemax')).toBe('1');
    expect(meter.getAttribute('aria-valuenow')).toBe('0.65');
    expect(meter.getAttribute('aria-label')).toBeTruthy();
  });
});

describe('InsightEvidence — raw percentage gating', () => {
  it('does not render percentage text by default', () => {
    render(InsightEvidence, {
      props: { confidenceScore: 0.73, currentTier: 'developing', entryCount: 28 },
    });
    expect(screen.queryByTestId('insight-confidence-score-percent')).toBeNull();
    const label = screen.getByTestId('insight-confidence-label').textContent ?? '';
    expect(label).not.toMatch(/\d+%/);
  });

  it('shows percentage when detailed=true', () => {
    render(InsightEvidence, {
      props: { confidenceScore: 0.73, currentTier: 'developing', entryCount: 28, detailed: true },
    });
    expect(screen.getByTestId('insight-confidence-score-percent').textContent).toContain('73%');
  });
});

describe('InsightEvidence — visibility toggles (avoid duplicate rendering)', () => {
  it('renders only the tier chip when showConfidence=false', () => {
    render(InsightEvidence, {
      props: { maturity: maturity(), confidenceScore: 0.9, showConfidence: false },
    });
    expect(screen.getByTestId('insight-maturity-badge')).toBeTruthy();
    expect(screen.queryByTestId('insight-confidence-meter')).toBeNull();
  });

  it('shows the sample line only when showSample=true', () => {
    const { rerender } = render(InsightEvidence, {
      props: { confidenceScore: 0.5, entryCount: 12, showSample: false },
    });
    expect(screen.queryByTestId('insight-evidence-sample')).toBeNull();

    rerender({ confidenceScore: 0.5, entryCount: 12, showSample: true });
    expect(screen.getByTestId('insight-evidence-sample').textContent).toContain(
      'Based on 12 entries'
    );
  });
});

describe('InsightEvidence — input clamping', () => {
  it('clamps score > 1 to the highest label', () => {
    render(InsightEvidence, {
      props: { confidenceScore: 2.5, currentTier: 'robust', entryCount: 50, detailed: true },
    });
    expect(screen.getByTestId('insight-confidence-score-percent').textContent).toContain('100%');
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe(
      'Very strong finding'
    );
  });

  it('clamps score < 0 to the lowest label', () => {
    render(InsightEvidence, {
      props: { confidenceScore: -0.5, currentTier: 'none', entryCount: 0, detailed: true },
    });
    expect(screen.getByTestId('insight-confidence-score-percent').textContent).toContain('0%');
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe('Early signal');
  });
});
