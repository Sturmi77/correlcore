import { expect, test, type Page } from '@playwright/test';

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
    if (path === '/entries') return json(200, []);
    return json(404, { detail: `Unhandled trends mock route: ${request.method()} ${path}` });
  });

  return { requestedRanges };
}

test('mobile trends starts with an understandable summary and no page overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const api = await installTrendsApi(page);
  await page.goto('/trends');

  const summary = page.getByTestId('mobile-trends-summary');
  await expect(summary).toBeVisible({ timeout: 60_000 });
  await expect(summary.getByText('Stress')).toBeVisible();
  await expect(summary.getByText('Focus')).toBeVisible();
  await expect(summary.getByText('Fatigue')).toBeVisible();
  await expect(page.getByTestId('mobile-trends-detail')).toBeVisible();
  await expect(page.getByTestId('mobile-trends-detail-toggle')).toHaveCount(0);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(0);

  await page.getByTestId('trends-range-month').click();
  await expect(page.getByTestId('trends-range-month')).toHaveAttribute('aria-pressed', 'true');
  await expect.poll(() => api.requestedRanges.includes('month')).toBe(true);
});

test('mobile compare filters and analysis canvas are reachable by scroll at 430px', async ({
  page,
}) => {
  await page.setViewportSize({ width: 430, height: 932 });
  await installTrendsApi(page);
  await page.goto('/trends');

  await expect(page.getByTestId('mobile-trends-summary')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('trends-compare-filters')).toBeVisible();
  await page.getByTestId('trends-compare-panel').scrollIntoViewIfNeeded();
  await expect(page.getByTestId('trends-compare-panel')).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
  ).toBeLessThanOrEqual(0);
});

test('mobile trends exposes an explicit empty summary', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installTrendsApi(page, { empty: true });
  await page.goto('/trends');
  await expect(page.getByTestId('mobile-trends-summary-empty')).toBeVisible({ timeout: 60_000 });
});

test('desktop keeps the full comparison canvas and filters visible', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installTrendsApi(page);
  await page.goto('/trends');
  await expect(page.getByTestId('trends-compare-panel')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('trends-compare-filters')).toBeVisible();
  await expect(page.getByTestId('mobile-trends-summary')).toHaveCount(0);
});
