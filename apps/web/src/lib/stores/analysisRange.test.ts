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

  it('persists the selected window in days', async () => {
    vi.stubGlobal('window', { ...globalThis.window });
    const { analysisRange, setAnalysisRange } = await import('./analysisRange');

    expect(get(analysisRange)).toBe(28);

    setAnalysisRange(90);
    expect(get(analysisRange)).toBe(90);
    expect(localStorage.getItem('cc_trend_window_days')).toBe('90');
    expect(localStorage.getItem('cc_analysis_range')).toBe('quarter');
  });

  it('migrates legacy co-occurrence range preference', async () => {
    localStorage.setItem('cc_insights_cooccurrence_range', '90d');
    const { analysisRange } = await import('./analysisRange');

    expect(get(analysisRange)).toBe(90);
  });

  it('migrates legacy TimeseriesRange storage', async () => {
    localStorage.setItem('cc_analysis_range', 'week');
    const { analysisRange } = await import('./analysisRange');

    expect(get(analysisRange)).toBe(14);
  });
});
