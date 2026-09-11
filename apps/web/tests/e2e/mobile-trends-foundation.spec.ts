import { expect, test, type Page } from '@playwright/test';
import { mockDashboardSummary, mockUserPreferences } from '../../src/lib/dev/mockEntries';

const user = {
  id: '00000000-0000-4000-8000-000000000092',
  email: 'mobile-trends@example.test',
  display_name: 'Mobile Trends',
  is_verified: true,
};

async function installTrendsApi(page: Page, options: { empty?: boolean } = {}) {
  const requestedRanges: string[] = [];
  await page.addInitScript(() => window.localStorage.setItem('correlcore-locale', 'en'));

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (path === '/auth/me') return json(200, user);
    if (path === '/auth/refresh') {
      return json(200, {
        access_token: 'trends-e2e-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }
    if (path === '/user/preferences') {
      return json(200, { ...mockUserPreferences, user_id: user.id });
    }
    if (path.startsWith('/dashboard/summary')) {
      return json(200, {
        ...mockDashboardSummary,
        entry_count: options.empty ? 0 : Math.max(mockDashboardSummary.entry_count, 2),
        work_context_summary: options.empty ? [] : mockDashboardSummary.work_context_summary,
        weekday_summary: options.empty ? [] : mockDashboardSummary.weekday_summary,
      });
    }
    if (path === '/insights' || path === '/insights/latest') {
      return json(200, { insight_maturity: null, insights: [] });
    }
    if (path === '/insights/dismissals') return json(200, { dismissals: [] });
    if (path === '/insights/tag-clusters') {
      return json(200, {
        status: 'insufficient_data',
        entry_count: 0,
        active_tag_count: 0,
        active_signal_count: 0,
        window_days: 90,
        k: null,
        reason: 'entry_count_below_30',
        cluster_kind: 'mixed',
        clusters: [],
      });
    }
    if (path.startsWith('/entries/stats/health-context')) {
      return json(200, {
        as_of: '2026-06-23',
        coverage_window_days: 90,
        maturity: {
          phase: 'robust',
          phase_index: 4,
          current_entries: 12,
          next_phase_at: 30,
          entries_until_next: 0,
        },
        coverage: {
          entry: { days_with_data: 12, window_days: 90, pct: 0.13 },
          sleep: { days_with_data: 0, window_days: 90, pct: 0 },
          symptom: { days_with_data: 2, window_days: 90, pct: 0.02 },
        },
        sections: [],
        health_connect: null,
      });
    }
    if (path === '/entries/stats/timeseries') {
      const range = url.searchParams.get('range') ?? 'week';
      requestedRanges.push(range);
      return json(200, {
        range,
        points: options.empty
          ? []
          : [
              {
                period_start: '2026-06-17',
                period_end: '2026-06-17',
                entry_count: 1,
                mood_avg: 3,
                energy_avg: 4,
                stress_avg: 4,
              },
              {
                period_start: '2026-06-23',
                period_end: '2026-06-23',
                entry_count: 1,
                mood_avg: 4,
                energy_avg: 3,
                stress_avg: 2,
              },
            ],
      });
    }
    if (path === '/entries/stats/tags') {
      return json(200, {
        start_date: '2026-06-17',
        end_date: '2026-06-23',
        tags: options.empty
          ? []
          : [
              {
                tag_id: 'focus',
                slug: 'focus',
                name: 'Focus',
                category: 'work',
                color: null,
                days: [
                  { date: '2026-06-21', count: 2 },
                  { date: '2026-06-23', count: 1 },
                ],
              },
            ],
      });
    }
    if (path === '/entries/stats/symptoms') {
      return json(200, {
        start_date: '2026-06-17',
        end_date: '2026-06-23',
        symptoms: options.empty
          ? []
          : [
              {
                symptom_id: 'fatigue',
                slug: 'fatigue',
                name: 'Fatigue',
                icon: null,
                days: [{ date: '2026-06-23', count: 2, max_intensity: 2 }],
              },
            ],
      });
    }
    if (path === '/entries/stats/streak') {
      return json(200, {
        current_streak: 3,
        longest_streak: 5,
        total_entry_days: 12,
        last_entry_date: '2026-06-23',
        as_of: '2026-06-23',
      });
    }
    if (path === '/habits') return json(200, { habits: [] });
    if (path === '/tags' || path === '/tags/default') return json(200, []);
    if (path === '/symptoms' || path === '/symptoms/default') return json(200, []);
    if (path === '/entries') {
      // Keep work-context days on the mocked timeseries axis (2026-06-17/23).
      // Compare loads a rolling year window; using the query bounds would place
      // rows outside the clamped June axis and prune "Office" (#590).
      return json(
        200,
        options.empty
          ? []
          : [
              {
                id: 'trend-entry-office',
                user_id: user.id,
                entry_date: '2026-06-23',
                slot: 'day',
                mood_score: 4,
                energy: 3,
                stress: 2,
                cycle_day: null,
                source: 'manual',
                work_context: 'office',
                note: null,
                created_at: '2026-06-23T09:00:00Z',
                updated_at: '2026-06-23T09:00:00Z',
              },
              {
                id: 'trend-entry-homeoffice',
                user_id: user.id,
                entry_date: '2026-06-17',
                slot: 'day',
                mood_score: 3,
                energy: 4,
                stress: 3,
                cycle_day: null,
                source: 'manual',
                work_context: 'homeoffice',
                note: null,
                created_at: '2026-06-17T09:00:00Z',
                updated_at: '2026-06-17T09:00:00Z',
              },
            ]
      );
    }
    return json(404, { detail: `Unhandled trends mock route: ${request.method()} ${path}` });
  });

  return { requestedRanges };
}

test('mobile home starts with an understandable trends summary and no page overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installTrendsApi(page);
  await page.goto('/');

  const summary = page.getByTestId('mobile-trends-summary');
  await expect(summary).toBeVisible({ timeout: 60_000 });
  await expect(summary.getByText('Stress')).toBeVisible();
  await expect(summary.getByText('Focus')).toBeVisible();
  await expect(summary.getByText('Fatigue')).toBeVisible();
  await expect(page.getByTestId('mobile-trends-summary-link')).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(0);
});

test('mobile compare filters and analysis canvas are reachable by scroll at 430px', async ({
  page,
}) => {
  await page.setViewportSize({ width: 430, height: 932 });
  await installTrendsApi(page);
  await page.goto('/trends');

  await expect(page.getByTestId('mobile-trends-detail')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('mobile-trends-summary')).toHaveCount(0);
  await expect(page.getByTestId('trends-compare-quick-filters')).toBeVisible();
  await page.getByTestId('trends-compare-customize').click();
  await expect(page.getByTestId('trends-compare-settings-sheet')).toBeVisible();
  await expect(page.getByTestId('trends-compare-filters')).toBeVisible();
  await page.getByTestId('trends-compare-settings-close').click();
  await page.getByTestId('trends-compare-panel').scrollIntoViewIfNeeded();
  await expect(page.getByTestId('trends-compare-panel')).toBeVisible();
  await page.getByTestId('trends-compare-customize').click();
  await expect(page.getByLabel('Work context')).toBeChecked();
  await page.getByLabel('Work context').uncheck();
  await page.getByTestId('trends-compare-settings-close').click();
  await expect(page.getByText('Office').first()).toHaveCount(0);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(0);
});

test('mobile home exposes an explicit empty trends summary', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installTrendsApi(page, { empty: true });
  await page.goto('/');
  await expect(page.getByTestId('mobile-trends-summary-empty')).toBeVisible({ timeout: 60_000 });
});

test('desktop keeps the full comparison canvas and filters visible', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installTrendsApi(page);
  await page.goto('/trends');
  await expect(page.getByTestId('trends-compare-panel')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('trends-compare-filters')).toBeVisible();
  await expect(page.getByLabel('Work context')).toBeChecked();
  await expect(page.getByText('Office').first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('mobile-trends-summary')).toHaveCount(0);
});
