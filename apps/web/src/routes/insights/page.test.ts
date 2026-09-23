import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setAnalysisRange } from '$lib/stores/analysisRange';
import { fetchTagCooccurrence, listLatestInsights, type InsightResponse } from '$lib/api/insights';
import { fetchSymptomHeatmap, type SymptomHeatmapResponse } from '$lib/api/stats';
import { listEntries, type EntryResponse } from '$lib/api/entries';
import Page from './+page.svelte';

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

type TagCooccurrenceRange = '7d' | '30d' | '90d' | '1y';

const testHelpers = vi.hoisted(() => {
  function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
      resolve = res;
    });
    return { promise, resolve };
  }

  const tagCooccurrenceRequests: Deferred<{
    range: TagCooccurrenceRange;
    start_date: string;
    end_date: string;
    min_count: number;
    pairs: {
      tag_a: {
        tag_id: string;
        slug: string;
        name: string;
        category: string;
        color: null;
      };
      tag_b: {
        tag_id: string;
        slug: string;
        name: string;
        category: string;
        color: null;
      };
      count: number;
      pct_of_a: number;
      pct_of_b: number;
    }[];
  }>[] = [];

  let pageValue = {
    url: new URL('http://localhost/insights'),
    params: {},
    route: { id: '/insights' },
    status: 200,
    error: null,
    data: {},
    form: null,
    state: {},
  };
  const pageSubscribers = new Set<(value: typeof pageValue) => void>();
  const pageStore = {
    subscribe(run: (value: typeof pageValue) => void) {
      pageSubscribers.add(run);
      run(pageValue);
      return () => pageSubscribers.delete(run);
    },
  };
  function setPageUrl(url: string): void {
    pageValue = { ...pageValue, url: new URL(url) };
    pageSubscribers.forEach((run) => run(pageValue));
  }
  let lastFeedProps: Record<string, unknown> = {};
  let lastMobileProps: Record<string, unknown> = {};
  function captureFeedProps(props: Record<string, unknown>): string {
    lastFeedProps = props;
    return `insight-feed:entries:${props.entryCount ?? 0}`;
  }
  function captureMobileProps(props: Record<string, unknown>): string {
    lastMobileProps = props;
    return 'mobile-insight-lead';
  }

  function mockComponent(testId: string, renderText?: (props: Record<string, unknown>) => string) {
    return function MockComponent(anchor: Element | Comment, props: Record<string, unknown> = {}) {
      const el = document.createElement('div');
      el.setAttribute('data-testid', testId);

      const update = () => {
        el.textContent = renderText?.(props) ?? testId;
      };

      update();
      const refresh = renderText ? setInterval(update, 1) : undefined;
      anchor.parentNode?.insertBefore(el, anchor);

      return {
        $on() {
          return () => {};
        },
        $set(nextProps: Record<string, unknown>) {
          props = { ...props, ...nextProps };
          update();
        },
        $destroy() {
          if (refresh) clearInterval(refresh);
          el.remove();
        },
      };
    };
  }

  return {
    captureFeedProps,
    captureMobileProps,
    deferred,
    get lastFeedProps() {
      return lastFeedProps;
    },
    get lastMobileProps() {
      return lastMobileProps;
    },
    mockComponent,
    pageStore,
    setPageUrl,
    tagCooccurrenceRequests,
  };
});

function tagCooccurrenceResponse(range: TagCooccurrenceRange) {
  const tag = (id: string) => ({
    tag_id: `${range}-${id}`,
    slug: `${range}-${id}`,
    name: `${range} tag ${id}`,
    category: 'test',
    color: null,
  });
  const pair = (a: string, b: string, count: number) => ({
    tag_a: tag(a),
    tag_b: tag(b),
    count,
    pct_of_a: 50,
    pct_of_b: 50,
  });

  return {
    range,
    start_date: '2026-05-01',
    end_date: '2026-05-31',
    min_count: 2,
    pairs: [
      pair('a', 'b', 5),
      pair('a', 'c', 4),
      pair('a', 'd', 3),
      pair('a', 'e', 2),
      pair('a', 'f', 2),
    ],
  };
}

function entryResponse(entryDate: string): EntryResponse {
  return {
    id: `entry-${entryDate}`,
    user_id: 'user-1',
    entry_date: entryDate,
    slot: 'day',
    mood_score: 4,
    energy: 4,
    stress: 2,
    cycle_day: null,
    source: 'direct',
    work_context: 'homeoffice',
    note: null,
    created_at: `${entryDate}T12:00:00Z`,
    updated_at: `${entryDate}T12:00:00Z`,
  };
}

function symptomHeatmapResponse(startDate: string): SymptomHeatmapResponse {
  return {
    start_date: startDate,
    end_date: startDate,
    symptoms: [],
  };
}

const provisionalMaturity = {
  phase: 'provisional' as const,
  phase_index: 3 as const,
  current_entries: 20,
  next_phase_at: 30,
  next_phase_label: 'Robust Insights',
  entries_until_next: 10,
  user_message_key: 'maturity.provisional.description',
};

function insightResponse(id: string, overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id,
    user_id: 'user-1',
    insight_type: 'correlation',
    subject_type: 'tag',
    subject_id: 'tag-a',
    subject_label: 'Tag A',
    metric: 'mood_score',
    statement: id,
    confidence: 0.8,
    effect_size: 0.5,
    sample_n: 20,
    tier: 'developing',
    flags: {},
    payload: {},
    generated_for_date: '2026-05-31',
    generated_at: '2026-05-31T00:00:00Z',
    created_at: '2026-05-31T00:00:00Z',
    updated_at: '2026-05-31T00:00:00Z',
    ...overrides,
  } as InsightResponse;
}

async function flushPromises(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
}

vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return {
    _: readable((key: string) => key),
  };
});

vi.mock('$app/stores', () => ({
  page: testHelpers.pageStore,
}));

vi.mock('$lib/stores/auth', async () => {
  const { readable } = await import('svelte/store');
  return {
    auth: readable({
      status: 'authenticated',
      user: { id: 'user-1', email: 'user@example.com' },
    }),
  };
});

vi.mock('$lib/stores/devMode', async () => {
  const { readable } = await import('svelte/store');
  return {
    devForceVisualizations: readable(false),
  };
});

vi.mock('$lib/api/entries', () => ({
  listEntries: vi.fn(async () => []),
}));

vi.mock('$lib/api/stats', () => ({
  fetchSymptomHeatmap: vi.fn(async () => ({
    start_date: '2026-05-01',
    end_date: '2026-05-31',
    symptoms: [],
  })),
}));

vi.mock('$lib/api/tags', () => ({
  listDefaultTags: vi.fn(async () => []),
  listTagsForEntry: vi.fn(async () => []),
  listVisibleTags: vi.fn(async () => []),
}));

vi.mock('$lib/api/symptoms', () => ({
  listSymptomsForEntry: vi.fn(async () => []),
  listVisibleSymptoms: vi.fn(async () => []),
}));

vi.mock('$lib/api/preferences', () => ({
  fetchUserPreferences: vi.fn(async () => ({
    user_id: 'user-1',
    analytics_enabled: true,
    digest_enabled: true,
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    onboarding_maturity_intro_seen: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
    last_seen_insight_at: null,
    // Explicit all-on so range/reload tests still mount optional tool sections.
    insight_sections_version: 2,
    insight_sections: [
      { key: 'stage_header', enabled: true },
      { key: 'insight_feed', enabled: true },
      { key: 'correlation_matrix', enabled: true },
      { key: 'lag_heatmap', enabled: true },
      { key: 'dismissed', enabled: true },
      { key: 'symptom_analytics', enabled: true },
      { key: 'tag_groups', enabled: true },
      { key: 'tag_cooccurrence', enabled: true },
    ],
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  })),
  updateUserPreferences: vi.fn(async (preferences) => preferences),
}));

vi.mock('$lib/api/insights', () => ({
  fetchTagClusters: vi.fn(async () => ({
    status: 'insufficient_data',
    entry_count: 0,
    active_tag_count: 0,
    active_signal_count: 0,
    window_days: 90,
    k: null,
    reason: 'entry_count_below_30',
    cluster_kind: 'mixed',
    clusters: [],
  })),
  fetchTagCooccurrence: vi.fn(() => {
    const request = testHelpers.deferred<ReturnType<typeof tagCooccurrenceResponse>>();
    testHelpers.tagCooccurrenceRequests.push(request);
    return request.promise;
  }),
  fetchSymptomTagCooccurrence: vi.fn(async ({ range }: { range?: TagCooccurrenceRange } = {}) => ({
    range: range ?? '30d',
    start_date: '2026-05-01',
    end_date: '2026-05-31',
    min_count: 3,
    cells: [],
  })),
  listLatestInsights: vi.fn(async () => ({
    insight_maturity: {
      phase: 'provisional',
      phase_index: 3,
      current_entries: 20,
      next_phase_at: 30,
      next_phase_label: 'Robust Insights',
      entries_until_next: 10,
      user_message_key: 'maturity.provisional.description',
    },
    insights: [],
  })),
  listInsights: vi.fn(async () => ({
    insight_maturity: {
      phase: 'provisional',
      phase_index: 3,
      current_entries: 20,
      next_phase_at: 30,
      next_phase_label: 'Robust Insights',
      entries_until_next: 10,
      user_message_key: 'maturity.provisional.description',
    },
    insights: [],
  })),
  listInsightDismissals: vi.fn(async () => ({ dismissals: [] })),
  createInsightDismissal: vi.fn(),
  deleteInsightDismissal: vi.fn(),
  deleteInsightDismissalByInsightId: vi.fn(),
  regenerateInsights: vi.fn(async () => ({
    insight_count: 0,
    generated_for_date: '2026-05-10',
    tag_clusters_status: 'insufficient_data',
  })),
  fetchInsightEventWindows: vi.fn(async () => ({
    range: '30d',
    start_date: '2026-05-01',
    end_date: '2026-05-31',
    events: [],
    points: [],
  })),
}));

vi.mock('$lib/components/insights/InsightFeed.svelte', () => ({
  default: testHelpers.mockComponent('insight-feed', testHelpers.captureFeedProps),
}));
vi.mock('$lib/components/insights/DismissedInsightsSection.svelte', () => ({
  default: testHelpers.mockComponent('dismissed-insights-section'),
}));
vi.mock('$lib/components/insights/InsightMatrix.svelte', () => ({
  default: testHelpers.mockComponent('insight-matrix'),
}));
vi.mock('$lib/components/insights/InsightStageHeader.svelte', () => ({
  default: testHelpers.mockComponent('insight-stage-header'),
}));
vi.mock('$lib/components/insights/MobileInsightLead.svelte', () => ({
  default: testHelpers.mockComponent('mobile-insight-lead', testHelpers.captureMobileProps),
}));
vi.mock('$lib/components/insights/CooccurrenceEntrySheet.svelte', () => ({
  default: testHelpers.mockComponent('cooccurrence-entry-sheet'),
}));
vi.mock('$lib/components/insights/CorrelationDisclaimer.svelte', () => ({
  default: testHelpers.mockComponent('correlation-disclaimer'),
}));
vi.mock('$lib/components/insights/TagGroupsSection.svelte', () => ({
  default: testHelpers.mockComponent('tag-groups-section'),
}));
vi.mock('$lib/components/insights/symptoms/SymptomAnalyticsSection.svelte', () => ({
  default: testHelpers.mockComponent(
    'symptom-analytics-section',
    (props: Record<string, unknown>) => {
      const heatmap = props.heatmap as SymptomHeatmapResponse | null;
      const entries = props.entries as EntryResponse[] | undefined;
      return `symptom-window:${heatmap?.start_date ?? 'none'}:entries:${entries?.length ?? 0}`;
    }
  ),
}));
vi.mock('$lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte', () => ({
  default: testHelpers.mockComponent('symptom-detail-sheet'),
}));
vi.mock('$lib/components/trends/EntryHistorySheet.svelte', () => ({
  default: testHelpers.mockComponent('entry-history-sheet'),
}));

afterEach(() => {
  cleanup();
});

describe('/insights page analysis range', () => {
  beforeEach(() => {
    testHelpers.tagCooccurrenceRequests.length = 0;
    localStorage.clear();
    testHelpers.setPageUrl('http://localhost/insights');
    setAnalysisRange(14);
    vi.clearAllMocks();
  });

  it('focuses the feed only when one insight proves both carried signals', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'symptom', id: 'symptom-a', label: 'Symptom A' },
        { kind: 'tag', id: 'tag-b', label: 'Tag B' },
      ],
    };
    testHelpers.setPageUrl(
      `http://localhost/insights?${new URLSearchParams({ pair: JSON.stringify(pair) })}`
    );
    const exactPairResponse = {
      insight_maturity: provisionalMaturity,
      insights: [
        insightResponse('exact-pair', {
          subject_type: 'composite',
          subject_id: null,
          subject_label: 'Symptom A + Tag B',
          payload: {
            kind: 'symptom_tag_cooccurrence',
            symptom_id: 'symptom-a',
            symptom_name: 'Symptom A',
            tag_id: 'tag-b',
            tag_name: 'Tag B',
          },
        }),
        insightResponse('only-one-pin', {
          subject_id: 'tag-b',
          subject_label: 'Tag B',
        }),
      ],
    };
    vi.mocked(listLatestInsights)
      .mockResolvedValueOnce(exactPairResponse)
      .mockResolvedValueOnce(exactPairResponse);

    render(Page);

    await waitFor(() => expect(screen.getByTestId('insights-carried-pair-focused')).toBeTruthy());
    const focusedIds = [
      ...(((testHelpers.lastMobileProps.insight as InsightResponse | undefined)?.id
        ? [testHelpers.lastMobileProps.insight as InsightResponse]
        : []) as InsightResponse[]),
      ...((testHelpers.lastFeedProps.insights as InsightResponse[] | undefined) ?? []),
    ].map((insight) => insight.id);
    expect(focusedIds).toEqual(['exact-pair']);
    expect(
      testHelpers.lastMobileProps.detailQuery ?? testHelpers.lastFeedProps.detailQuery
    ).toContain('pair=');
  });

  it('shows no pair match only after a successful search', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'tag', id: 'missing-a' },
        { kind: 'tag', id: 'missing-b' },
      ],
    };
    testHelpers.setPageUrl(
      `http://localhost/insights?${new URLSearchParams({ pair: JSON.stringify(pair) })}`
    );
    vi.mocked(listLatestInsights).mockResolvedValueOnce({
      insight_maturity: provisionalMaturity,
      insights: [insightResponse('unrelated')],
    });

    render(Page);

    await waitFor(() =>
      expect(screen.getByTestId('insights-carried-signals-unmatched')).toBeTruthy()
    );
  });

  it('keeps API failures separate from a semantic no-match result', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'tag', id: 'tag-a' },
        { kind: 'tag', id: 'tag-b' },
      ],
    };
    testHelpers.setPageUrl(
      `http://localhost/insights?${new URLSearchParams({ pair: JSON.stringify(pair) })}`
    );
    vi.mocked(listLatestInsights).mockRejectedValueOnce(new Error('offline'));

    render(Page);

    await waitFor(() => expect(testHelpers.lastFeedProps.error).toBe('offline'));
    expect(screen.queryByTestId('insights-carried-signals-unmatched')).toBeNull();
  });

  it('reloads requested analytics on range change and ignores stale co-occurrence responses', async () => {
    render(Page);

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '7d', min_count: 2 });
    });

    await fireEvent.click(screen.getByTestId('insights-range-90'));

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '90d', min_count: 2 });
    });

    testHelpers.tagCooccurrenceRequests[1]?.resolve(tagCooccurrenceResponse('90d'));

    await waitFor(() => {
      expect(screen.getAllByText('90d tag a').length).toBeGreaterThan(0);
    });
    expect(screen.queryByText('7d tag a')).toBeNull();

    testHelpers.tagCooccurrenceRequests[0]?.resolve(tagCooccurrenceResponse('7d'));
    await flushPromises();

    expect(screen.getAllByText('90d tag a').length).toBeGreaterThan(0);
    expect(screen.queryByText('7d tag a')).toBeNull();
  });

  it('reloads symptom analytics for the selected analysis range', async () => {
    render(Page);

    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalled();
    });

    const initialCall = vi.mocked(fetchSymptomHeatmap).mock.calls.at(-1)?.[0];
    expect(initialCall?.start_date).toBeTruthy();
    expect(initialCall?.end_date).toBeTruthy();

    vi.mocked(fetchSymptomHeatmap).mockClear();
    vi.mocked(listEntries).mockClear();

    await fireEvent.click(screen.getByTestId('insights-range-90'));

    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalled();
      expect(listEntries).toHaveBeenCalled();
    });

    const nextHeatmapCall = vi.mocked(fetchSymptomHeatmap).mock.calls.at(-1)?.[0];
    const nextEntriesCall = vi.mocked(listEntries).mock.calls.at(-1)?.[0];
    expect(nextHeatmapCall?.start_date).not.toBe(initialCall?.start_date);
    expect(nextEntriesCall?.start_date).toBe(nextHeatmapCall?.start_date);
    expect(nextEntriesCall?.end_date).toBe(nextHeatmapCall?.end_date);
  });

  it('does not mix symptom heatmap and entry windows when a range reload partially fails', async () => {
    vi.mocked(fetchSymptomHeatmap).mockResolvedValueOnce(symptomHeatmapResponse('2026-06-01'));
    vi.mocked(listEntries).mockResolvedValueOnce([
      entryResponse('2026-06-01'),
      entryResponse('2026-06-02'),
    ]);

    render(Page);

    await waitFor(() => {
      expect(screen.getByText('symptom-window:2026-06-01:entries:2')).toBeTruthy();
      expect(screen.getByText('insight-feed:entries:2')).toBeTruthy();
    });
    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalledTimes(1);
      expect(listEntries).toHaveBeenCalledTimes(1);
    });
    await flushPromises();

    vi.mocked(fetchSymptomHeatmap).mockClear().mockRejectedValueOnce(new Error('timeout'));
    vi.mocked(listEntries)
      .mockClear()
      .mockResolvedValueOnce([entryResponse('2025-07-01')]);

    await fireEvent.click(screen.getByTestId('insights-range-90'));

    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalledTimes(1);
      expect(listEntries).toHaveBeenCalledTimes(1);
    });
    await flushPromises();

    expect(screen.queryByText('symptom-window:2026-06-01:entries:1')).toBeNull();
    expect(screen.queryByText('insight-feed:entries:1')).toBeNull();
    await waitFor(() => {
      expect(screen.getByText('insight-feed:entries:0')).toBeTruthy();
    });
  });

  it('ignores stale symptom analytics responses after rapid range changes', async () => {
    render(Page);

    await waitFor(() => {
      expect(screen.getByText('insight-feed:entries:0')).toBeTruthy();
    });

    const staleEntries = testHelpers.deferred<EntryResponse[]>();
    const staleHeatmap = testHelpers.deferred<SymptomHeatmapResponse>();
    vi.mocked(listEntries)
      .mockClear()
      .mockReturnValueOnce(staleEntries.promise)
      .mockResolvedValueOnce([entryResponse('2026-06-30'), entryResponse('2026-07-01')]);
    vi.mocked(fetchSymptomHeatmap)
      .mockClear()
      .mockReturnValueOnce(staleHeatmap.promise)
      .mockResolvedValueOnce(symptomHeatmapResponse('fresh-month-window'));

    await fireEvent.click(screen.getByTestId('insights-range-90'));
    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalledTimes(1);
    });

    await fireEvent.click(screen.getByTestId('insights-range-28'));
    await waitFor(() => {
      expect(fetchSymptomHeatmap).toHaveBeenCalledTimes(2);
      expect(screen.getByText('insight-feed:entries:2')).toBeTruthy();
    });

    staleEntries.resolve([entryResponse('2025-07-01')]);
    staleHeatmap.resolve(symptomHeatmapResponse('stale-90d-window'));
    await flushPromises();

    expect(screen.getByText('insight-feed:entries:2')).toBeTruthy();
    expect(screen.queryByText('insight-feed:entries:1')).toBeNull();
  });

  it('refetches co-occurrence when switching from week to month API windows', async () => {
    render(Page);

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '7d', min_count: 2 });
    });

    await fireEvent.click(screen.getByTestId('insights-range-28'));

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '30d', min_count: 2 });
    });

    expect(fetchTagCooccurrence).toHaveBeenCalledTimes(2);
  });
});
