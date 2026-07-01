import { get } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('analysisRange store', () => {
  beforeEach(() => {
    vi.resetModules();
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('persists the selected range', async () => {
    vi.stubGlobal('window', { ...globalThis.window });
    const { analysisRange, setAnalysisRange } = await import('./analysisRange');

    expect(get(analysisRange)).toBe('week');

    setAnalysisRange('quarter');
    expect(get(analysisRange)).toBe('quarter');
    expect(localStorage.getItem('cc_analysis_range')).toBe('quarter');
  });

  it('migrates legacy co-occurrence range preference', async () => {
    localStorage.setItem('cc_insights_cooccurrence_range', '90d');
    const { analysisRange } = await import('./analysisRange');

    expect(get(analysisRange)).toBe('quarter');
  });
});
