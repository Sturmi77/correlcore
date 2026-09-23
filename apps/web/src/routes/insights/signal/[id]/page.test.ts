import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { InsightResponse } from '$lib/api/insights';
import { fetchSymptomHeatmap } from '$lib/api/stats';
import Page from './+page.svelte';

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

const testHelpers = vi.hoisted(() => {
  function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((done) => {
      resolve = done;
    });
    return { promise, resolve };
  }

  const detailRequests: { id: string; deferred: Deferred<InsightResponse> }[] = [];
  let lastEsmProps: Record<string, unknown> = {};
  let pageValue = {
    url: new URL('http://localhost/insights/signal/a'),
    params: { id: 'a' },
    route: { id: '/insights/signal/[id]' },
    status: 200,
    error: null,
    data: {},
    form: null,
    state: {},
  };
  const subscribers = new Set<(value: typeof pageValue) => void>();
  const pageStore = {
    subscribe(run: (value: typeof pageValue) => void) {
      subscribers.add(run);
      run(pageValue);
      return () => subscribers.delete(run);
    },
  };
  function navigate(id: string, query = ''): void {
    pageValue = {
      ...pageValue,
      params: { id },
      url: new URL(`http://localhost/insights/signal/${id}${query}`),
    };
    subscribers.forEach((run) => run(pageValue));
  }

  function mockComponent(testId: string, capture?: (props: Record<string, unknown>) => void) {
    return function MockComponent(anchor: Element | Comment, initialProps = {}) {
      let props: Record<string, unknown> = initialProps;
      const element = document.createElement('div');
      element.dataset.testid = testId;
      capture?.(props);
      anchor.parentNode?.insertBefore(element, anchor);
      return {
        $on() {
          return () => {};
        },
        $set(nextProps: Record<string, unknown>) {
          props = { ...props, ...nextProps };
          capture?.(props);
        },
        $destroy() {
          element.remove();
        },
      };
    };
  }

  return {
    captureEsmProps(props: Record<string, unknown>) {
      lastEsmProps = props;
    },
    deferred,
    detailRequests,
    get lastEsmProps() {
      return lastEsmProps;
    },
    mockComponent,
    navigate,
    pageStore,
    resetEsmProps() {
      lastEsmProps = {};
    },
  };
});

function insight(id: string, overrides: Partial<InsightResponse> = {}): InsightResponse {
  return {
    id,
    user_id: 'user-1',
    insight_type: 'correlation',
    subject_type: 'tag',
    subject_id: `tag-${id}`,
    subject_label: `Tag ${id.toUpperCase()}`,
    metric: 'mood_score',
    statement: `Statement ${id.toUpperCase()}`,
    confidence: 0.8,
    effect_size: 0.5,
    sample_n: 20,
    tier: 'developing',
    flags: {},
    payload: {},
    generated_for_date: '2026-09-22',
    generated_at: '2026-09-22T00:00:00Z',
    created_at: '2026-09-22T00:00:00Z',
    updated_at: '2026-09-22T00:00:00Z',
    ...overrides,
  };
}

vi.mock('$app/stores', () => ({ page: testHelpers.pageStore }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('svelte-i18n', async () => {
  const { readable } = await import('svelte/store');
  return { _: readable((key: string) => key) };
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
vi.mock('$lib/stores/pageRefresh', () => ({
  registerPageRefresh: vi.fn(() => () => {}),
}));
vi.mock('$lib/api/insights', () => ({
  fetchInsight: vi.fn((id: string) => {
    const request = testHelpers.deferred<InsightResponse>();
    testHelpers.detailRequests.push({ id, deferred: request });
    return request.promise;
  }),
  fetchInsightVerification: vi.fn(async (id: string) => ({
    range: '90d',
    start_date: '2026-06-25',
    end_date: '2026-09-22',
    metric: 'mood_score',
    subject_label: `Tag ${id.toUpperCase()}`,
    points: [],
    with_mean: null,
    without_mean: null,
    with_se: null,
    without_se: null,
    with_n: 0,
    without_n: 0,
  })),
  fetchInsightEventWindows: vi.fn(async () => ({
    range: '90d',
    start_date: '2026-07-01',
    end_date: '2026-09-22',
    events: [{ onset: '2026-09-20', label: 'Tag A' }],
    points: [],
  })),
  listLatestInsights: vi.fn(async () => ({
    insight_maturity: {
      phase: 'robust',
      phase_index: 4,
      current_entries: 40,
      next_phase_at: null,
      next_phase_label: null,
      entries_until_next: null,
      user_message_key: 'maturity.robust.description',
    },
    insights: [],
  })),
}));
vi.mock('$lib/api/stats', () => ({
  fetchTagHeatmap: vi.fn(async () => ({
    start_date: '2026-06-24',
    end_date: '2026-09-29',
    tags: [],
  })),
  fetchSymptomHeatmap: vi.fn(async () => ({
    start_date: '2026-06-24',
    end_date: '2026-09-29',
    symptoms: [
      {
        symptom_id: 'symptom-b',
        name: 'Symptom B',
        slug: 'symptom-b',
        icon: null,
        days: [{ date: '2026-09-20', count: 1, max_intensity: 2 }],
      },
    ],
  })),
}));
vi.mock('$lib/api/entries', () => ({ listEntries: vi.fn(async () => []) }));

vi.mock('$lib/components/insights/InsightEvidence.svelte', () => ({
  default: testHelpers.mockComponent('insight-evidence'),
}));
vi.mock('$lib/components/insights/WithWithoutDistribution.svelte', () => ({
  default: testHelpers.mockComponent('with-without-distribution'),
}));
vi.mock('$lib/components/insights/SignalScatter.svelte', () => ({
  default: testHelpers.mockComponent('signal-scatter'),
}));
vi.mock('$lib/components/insights/SignalLagEvidence.svelte', () => ({
  default: testHelpers.mockComponent('signal-lag-evidence'),
}));
vi.mock('$lib/components/trends/EventAlignedSmallMultiplesSheet.svelte', () => ({
  default: testHelpers.mockComponent('event-aligned-small-multiples', testHelpers.captureEsmProps),
}));

afterEach(cleanup);

describe('/insights/signal/[id]', () => {
  beforeEach(() => {
    testHelpers.detailRequests.length = 0;
    testHelpers.resetEsmProps();
    testHelpers.navigate('a');
    vi.clearAllMocks();
  });

  it('reloads a reused route by id and ignores the superseded response', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'tag', id: 'tag-a' },
        { kind: 'tag', id: 'tag-b' },
      ],
    };
    const query = `?${new URLSearchParams({ pair: JSON.stringify(pair) })}`;
    testHelpers.navigate('a', query);
    render(Page);
    await waitFor(() => expect(testHelpers.detailRequests.map((row) => row.id)).toEqual(['a']));

    testHelpers.navigate('b', query);
    await waitFor(() =>
      expect(testHelpers.detailRequests.map((row) => row.id)).toEqual(['a', 'b'])
    );
    testHelpers.detailRequests[1].deferred.resolve(insight('b'));
    await waitFor(() => expect(screen.getByText('Statement B')).toBeTruthy());

    testHelpers.detailRequests[0].deferred.resolve(insight('a'));
    await Promise.resolve();
    expect(screen.queryByText('Statement A')).toBeNull();
    expect(screen.getByText('Statement B')).toBeTruthy();

    const reportLink = screen.getByTestId('signal-report-link') as HTMLAnchorElement;
    expect(new URL(reportLink.href).searchParams.get('signal')).toBe('b');
    expect(new URL(reportLink.href).searchParams.get('pair')).toBe(JSON.stringify(pair));

    testHelpers.navigate('a', query);
    await waitFor(() => expect(testHelpers.detailRequests).toHaveLength(3));
    testHelpers.detailRequests[2].deferred.resolve(insight('a'));
    await waitFor(() => expect(screen.getByText('Statement A')).toBeTruthy());
  });

  it('keeps the carried partner fixed when opening ESM from detail', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'tag', id: 'tag-a', label: 'Tag A' },
        { kind: 'symptom', id: 'symptom-b', label: 'Symptom B' },
      ],
    };
    testHelpers.navigate('a', `?${new URLSearchParams({ pair: JSON.stringify(pair) }).toString()}`);
    render(Page);
    await waitFor(() => expect(testHelpers.detailRequests).toHaveLength(1));
    testHelpers.detailRequests[0].deferred.resolve(
      insight('a', {
        payload: {
          features: [{ kind: 'symptom', id: 'symptom-b', name: 'Symptom B' }],
        },
      })
    );
    await waitFor(() => expect(screen.getByTestId('signal-open-esm')).toBeTruthy());

    await fireEvent.click(screen.getByTestId('signal-open-esm'));

    await waitFor(() =>
      expect(testHelpers.lastEsmProps.partner).toEqual({
        id: 'symptom-b',
        label: 'Symptom B',
        kind: 'symptom',
      })
    );
    expect(testHelpers.lastEsmProps.partnerPresenceDates).toEqual(['2026-09-20']);
  });

  it('opens ESM while optional partner presence is still loading', async () => {
    const pair = {
      version: 1,
      signals: [
        { kind: 'tag', id: 'tag-a' },
        { kind: 'symptom', id: 'symptom-b' },
      ],
    };
    const partnerRequest = testHelpers.deferred<Awaited<ReturnType<typeof fetchSymptomHeatmap>>>();
    vi.mocked(fetchSymptomHeatmap).mockReturnValueOnce(partnerRequest.promise);
    testHelpers.navigate('a', `?${new URLSearchParams({ pair: JSON.stringify(pair) }).toString()}`);
    render(Page);
    await waitFor(() => expect(testHelpers.detailRequests).toHaveLength(1));
    testHelpers.detailRequests[0].deferred.resolve(
      insight('a', {
        payload: { features: [{ kind: 'symptom', id: 'symptom-b', name: 'Symptom B' }] },
      })
    );
    await waitFor(() => expect(screen.getByTestId('signal-open-esm')).toBeTruthy());

    await fireEvent.click(screen.getByTestId('signal-open-esm'));

    await waitFor(() => expect(testHelpers.lastEsmProps.open).toBe(true));
    expect(testHelpers.lastEsmProps.partnerLoading).toBe(true);
    partnerRequest.resolve({ start_date: '2026-06-24', end_date: '2026-09-29', symptoms: [] });
    await waitFor(() => expect(testHelpers.lastEsmProps.partnerLoading).toBe(false));
  });
});
