import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { setAnalysisRange } from '$lib/stores/analysisRange';
import { fetchTagCooccurrence } from '$lib/api/insights';
import Page from './+page.svelte';

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

type TagCooccurrenceRange = '30d' | '90d' | '1y';

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

  function mockComponent(testId: string, renderText?: (props: Record<string, unknown>) => string) {
    return function MockComponent(anchor: Element | Comment, props: Record<string, unknown> = {}) {
      const el = document.createElement('div');
      el.setAttribute('data-testid', testId);

      const update = () => {
        el.textContent = renderText?.(props) ?? testId;
      };

      update();
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
          el.remove();
        },
      };
    };
  }

  return { deferred, mockComponent, tagCooccurrenceRequests };
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
    onboarding_retro_completed: true,
    onboarding_profile_completed: true,
    dismissed_insight_keys: [],
    reached_milestone_keys: [],
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
    reason: 'entry_count_below_90',
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
}));

vi.mock('$lib/components/insights/InsightFeed.svelte', () => ({
  default: testHelpers.mockComponent('insight-feed'),
}));
vi.mock('$lib/components/insights/InsightMatrix.svelte', () => ({
  default: testHelpers.mockComponent('insight-matrix'),
}));
vi.mock('$lib/components/insights/InsightStageHeader.svelte', () => ({
  default: testHelpers.mockComponent('insight-stage-header'),
}));
vi.mock('$lib/components/insights/MobileInsightLead.svelte', () => ({
  default: testHelpers.mockComponent('mobile-insight-lead'),
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
  default: testHelpers.mockComponent('symptom-analytics-section'),
}));
vi.mock('$lib/components/insights/symptoms/SymptomCooccurrenceDetailSheet.svelte', () => ({
  default: testHelpers.mockComponent('symptom-detail-sheet'),
}));
vi.mock('$lib/components/trends/EntryHistorySheet.svelte', () => ({
  default: testHelpers.mockComponent('entry-history-sheet'),
}));

describe('/insights page analysis range', () => {
  beforeEach(() => {
    testHelpers.tagCooccurrenceRequests.length = 0;
    localStorage.clear();
    setAnalysisRange('week');
    vi.clearAllMocks();
  });

  it('reloads requested analytics on range change and ignores stale co-occurrence responses', async () => {
    render(Page);

    await fireEvent.click(await screen.findByText('insights.page.analytics_summary'));

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '30d', min_count: 2 });
    });

    await fireEvent.click(screen.getByTestId('insights-range-year'));

    await waitFor(() => {
      expect(fetchTagCooccurrence).toHaveBeenCalledWith({ range: '1y', min_count: 2 });
    });

    testHelpers.tagCooccurrenceRequests[1]?.resolve(tagCooccurrenceResponse('1y'));

    await waitFor(() => {
      expect(screen.getAllByText('1y tag a').length).toBeGreaterThan(0);
    });
    expect(screen.queryByText('30d tag a')).toBeNull();

    testHelpers.tagCooccurrenceRequests[0]?.resolve(tagCooccurrenceResponse('30d'));
    await flushPromises();

    expect(screen.getAllByText('1y tag a').length).toBeGreaterThan(0);
    expect(screen.queryByText('30d tag a')).toBeNull();
  });
});
