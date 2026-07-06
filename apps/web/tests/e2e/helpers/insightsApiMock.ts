import type { Page } from '@playwright/test';
import { mockInsightMaturity, mockInsights } from '../../../src/lib/dev/mockInsights';
import { mockEntries, mockUserPreferences } from '../../../src/lib/dev/mockEntries';
import {
  mockSymptomHeatmap,
  mockSymptomTagCooccurrenceByRange,
  mockTagClusters,
  mockTagCooccurrenceByRange,
} from '../../../src/lib/dev/mockTrends';

const user = {
  id: '00000000-0000-4000-8000-000000000008',
  email: 'mobile-insights@example.com',
  display_name: 'Mobile Insights',
  is_verified: true,
};

const preferences = {
  ...mockUserPreferences,
  user_id: user.id,
};

function json(route: import('@playwright/test').Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}

type InsightsApiMockOptions = {
  includeContextInsight?: boolean;
};

const contextInsight = {
  id: '20000000-0000-4000-8000-000000000context',
  user_id: user.id,
  insight_type: 'work_context_pattern',
  tier: 'early',
  metric: 'mood_score',
  subject_type: 'work_context',
  subject_id: null,
  subject_label: 'Office',
  effect_size: 0.31,
  confidence: 0.49,
  sample_n: 9,
  statement: 'Office days currently sit above your overall mood average in this early sample.',
  flags: { causal_claim: false, early_pattern: true },
  payload: {
    work_context: 'office',
    work_context_label: 'Office',
    context_count: 4,
    comparison_count: 5,
    context_mean: 4.1,
    overall_mean: 3.2,
    early_pattern: true,
  },
  generated_for_date: '2026-06-30',
  generated_at: '2026-06-30T09:00:00Z',
  created_at: '2026-06-30T09:00:00Z',
  updated_at: '2026-06-30T09:00:00Z',
} as const;

/** Auth + insights API mocks for mobile insights E2E (API-backed; dev_force_viz optional). */
export async function installInsightsApiMock(
  page: Page,
  options: InsightsApiMockOptions = {}
): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
    window.localStorage.setItem('cc_insights_symptoms', 'true');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    const method = request.method();

    if (path === '/auth/me' && method === 'GET') return json(route, 200, user);
    if (path === '/auth/refresh' && method === 'POST') {
      return json(route, 200, {
        access_token: 'insights-e2e-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }
    if (path === '/user/preferences' && method === 'GET') return json(route, 200, preferences);
    if (path === '/entries' && method === 'GET') return json(route, 200, mockEntries);
    if ((path === '/tags' || path === '/tags/default') && method === 'GET') {
      return json(route, 200, []);
    }
    if ((path === '/symptoms' || path === '/symptoms/default') && method === 'GET') {
      return json(route, 200, []);
    }
    if (path.startsWith('/entries/stats/symptoms') && method === 'GET') {
      return json(route, 200, mockSymptomHeatmap);
    }
    if (path.startsWith('/entries/stats/tags') && method === 'GET') {
      return json(route, 200, {
        start_date: mockSymptomHeatmap.start_date,
        end_date: mockSymptomHeatmap.end_date,
        tags: [],
      });
    }
    if (path.startsWith('/entries/stats/streak') && method === 'GET') {
      return json(route, 200, {
        current_streak: 6,
        longest_streak: 9,
        total_entry_days: mockEntries.length,
        last_entry_date: mockEntries[0]?.entry_date ?? null,
        as_of: mockEntries[0]?.entry_date ?? '2026-06-30',
      });
    }
    if (path.startsWith('/insights/tag-cooccurrence') && method === 'GET') {
      const range = (url.searchParams.get('range') ??
        '90d') as keyof typeof mockTagCooccurrenceByRange;
      return json(
        route,
        200,
        mockTagCooccurrenceByRange[range] ?? mockTagCooccurrenceByRange['90d']
      );
    }
    if (path === '/insights/tag-clusters' && method === 'GET') {
      return json(route, 200, mockTagClusters);
    }
    if (path.startsWith('/insights/symptom-tag-cooccurrence') && method === 'GET') {
      const range = (url.searchParams.get('range') ??
        '90d') as keyof typeof mockSymptomTagCooccurrenceByRange;
      return json(
        route,
        200,
        mockSymptomTagCooccurrenceByRange[range] ?? mockSymptomTagCooccurrenceByRange['90d']
      );
    }
    if ((path === '/insights' || path === '/insights/latest') && method === 'GET') {
      return json(route, 200, {
        insight_maturity: mockInsightMaturity,
        insights: options.includeContextInsight ? [...mockInsights, contextInsight] : mockInsights,
      });
    }

    return json(route, 404, {
      detail: `Unhandled mobile insights route: ${method} ${path}`,
    });
  });
}
