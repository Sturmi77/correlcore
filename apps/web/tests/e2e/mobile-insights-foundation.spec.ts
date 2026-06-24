import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000008',
  email: 'mobile-insights@example.com',
  display_name: 'Mobile Insights',
  is_verified: true,
};

async function installInsightsMockMode(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
    window.localStorage.setItem('dev_mode_enabled', 'true');
    window.localStorage.setItem('dev_force_viz', 'true');
    window.localStorage.setItem('cc_insights_symptoms', 'true');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');

    if (path === '/auth/me' && request.method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(user),
      });
    }

    return route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({
        detail: `Unhandled mobile insights route: ${request.method()} ${path}`,
      }),
    });
  });
}

test('390px prioritizes the strongest signal, confidence, and maturity', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installInsightsMockMode(page);
  await page.goto('/insights');

  const lead = page.getByTestId('mobile-insight-lead');
  const confidence = page.getByTestId('insight-card-confidence-summary');
  const maturity = page.getByTestId('mobile-insight-maturity');
  const viewTabs = page.getByTestId('insights-view-tabs');

  await expect(lead).toBeVisible();
  await expect(lead.getByText(/mood.*Energy/i)).toBeVisible();
  await expect(confidence).toBeVisible();
  await expect(page.getByTestId('insight-confidence-score-percent')).toHaveCount(0);
  await expect(page.getByTestId('mobile-insight-correlation-note')).toBeVisible();
  await expect(maturity).toBeVisible();

  const order = await page.evaluate(() => {
    const leadNode = document.querySelector('[data-testid="mobile-insight-lead"]');
    const tabsNode = document.querySelector('[data-testid="insights-view-tabs"]');
    return Boolean(leadNode && tabsNode && leadNode.compareDocumentPosition(tabsNode) & 4);
  });
  expect(order).toBe(true);
  await expect(viewTabs).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('430px keeps matrices and analytics behind explicit detail actions', async ({ page }) => {
  await page.setViewportSize({ width: 430, height: 932 });
  await installInsightsMockMode(page);
  await page.goto('/insights');

  await page.getByTestId('insights-view-matrix').tap();
  await expect(page.getByTestId('insight-matrix')).toBeVisible();
  await expect(page.getByTestId('mobile-insight-lead')).toHaveCount(0);

  await page.getByTestId('insights-view-findings').tap();
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible();
  await page.getByTestId('insight-feed-tab-symptoms').tap();
  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  await page.getByText('Deepen analysis', { exact: true }).tap();
  await expect(page.getByRole('heading', { name: 'Patterns', exact: true })).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('desktop preserves the existing analysis-first composition', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installInsightsMockMode(page);
  await page.goto('/insights');

  await expect(page.getByTestId('mobile-insight-lead')).toHaveCount(0);
  await expect(page.getByTestId('insight-stage-header')).toBeVisible();
  await expect(page.getByTestId('insight-feed')).toBeVisible();
  await expect(page.getByTestId('insight-card')).toHaveCount(4);

  await page.getByTestId('insights-view-matrix').click();
  await expect(page.getByTestId('insight-matrix')).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});
