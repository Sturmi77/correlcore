/**
 * InsightConfidenceScale — ADR-0018 tests.
 *
 * Covers:
 * 1. All 5 semantic label boundaries
 * 2. role="meter" + ARIA attributes
 * 3. No raw percentage text in default (collapsed) render
 * 4. Raw percentage visible only when showRawPercent=true
 * 5. Clamping of out-of-range inputs
 */
import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import InsightConfidenceScale from './InsightConfidenceScale.svelte';

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string, options?: { values?: { n?: number } }) => {
      const map: Record<string, string> = {
        'insights.confidence_label.early_signal': 'Early signal',
        'insights.confidence_label.emerging_pattern': 'Emerging pattern',
        'insights.confidence_label.moderate_finding': 'Moderate finding',
        'insights.confidence_label.strong_finding': 'Strong finding',
        'insights.confidence_label.very_strong_finding': 'Very strong finding',
        'home.confidence_scale.heading': 'Insight quality',
      };
      if (key === 'home.confidence_scale.entry_count')
        return `Based on ${options?.values?.n} entries`;
      return map[key] ?? key;
    }),
  };
});

describe('InsightConfidenceScale — semantic labels (ADR-0018)', () => {
  const labelCases = [
    { score: 0.0,  label: 'Early signal',        fill: '0%'  },
    { score: 0.1,  label: 'Early signal',        fill: '10%' },
    { score: 0.19, label: 'Early signal',        fill: '19%' },
    { score: 0.2,  label: 'Emerging pattern',    fill: '20%' },
    { score: 0.39, label: 'Emerging pattern',    fill: '39%' },
    { score: 0.4,  label: 'Moderate finding',    fill: '40%' },
    { score: 0.59, label: 'Moderate finding',    fill: '59%' },
    { score: 0.6,  label: 'Strong finding',      fill: '60%' },
    { score: 0.79, label: 'Strong finding',      fill: '79%' },
    { score: 0.8,  label: 'Very strong finding', fill: '80%' },
    { score: 1.0,  label: 'Very strong finding', fill: '100%' },
  ] as const;

  it.each(labelCases)('score $score → label "$label"', ({ score, label, fill }) => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: score, currentTier: 'robust', entryCount: 30 },
    });
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe(label);
    expect(screen.getByTestId('insight-confidence-fill').getAttribute('style')).toContain(
      `width: ${fill}`
    );
  });
});

describe('InsightConfidenceScale — ARIA (ADR-0018)', () => {
  it('exposes role=meter with correct aria attributes', () => {
    render(InsightConfidenceScale, {
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

describe('InsightConfidenceScale — no raw percentage in collapsed state', () => {
  it('does not render percentage text by default', () => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: 0.73, currentTier: 'developing', entryCount: 28 },
    });
    expect(screen.queryByTestId('insight-confidence-score-percent')).toBeNull();
    // Label text must not contain a bare percentage
    const label = screen.getByTestId('insight-confidence-label').textContent ?? '';
    expect(label).not.toMatch(/\d+%/);
  });

  it('shows percentage when showRawPercent=true', () => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: 0.73, currentTier: 'developing', entryCount: 28, showRawPercent: true },
    });
    expect(screen.getByTestId('insight-confidence-score-percent')).toBeTruthy();
  });
});

describe('InsightConfidenceScale — input clamping', () => {
  it('clamps score > 1 to 100%', () => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: 2.5, currentTier: 'robust', entryCount: 50 },
    });
    expect(screen.getByTestId('insight-confidence-fill').getAttribute('style')).toContain('width: 100%');
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe('Very strong finding');
  });

  it('clamps score < 0 to 0%', () => {
    render(InsightConfidenceScale, {
      props: { confidenceScore: -0.5, currentTier: 'none', entryCount: 0 },
    });
    expect(screen.getByTestId('insight-confidence-fill').getAttribute('style')).toContain('width: 0%');
    expect(screen.getByTestId('insight-confidence-label').textContent?.trim()).toBe('Early signal');
  });
});
