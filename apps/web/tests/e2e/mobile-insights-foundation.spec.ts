import { expect, test } from '@playwright/test';
import { installInsightsApiMock } from './helpers/insightsApiMock';

test.use({ hasTouch: true });

test('390px prioritizes the strongest signal, confidence, and maturity', async ({ page }) => {
  test.setTimeout(60_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await installInsightsApiMock(page);
  await page.goto('/insights');

  const lead = page.getByTestId('mobile-insight-lead');
  const confidence = page.getByTestId('insight-card-confidence-summary');
  const findingsToolbar = page.getByTestId('insights-findings-toolbar');

  await expect(findingsToolbar).toBeVisible({ timeout: 30_000 });
  await expect(lead).toBeVisible({ timeout: 30_000 });
  await expect(lead.getByTestId('insight-card-title')).toContainText(/Energy/i);
  await expect(confidence).toBeVisible();
  await expect(page.getByTestId('insight-confidence-score-percent')).toHaveCount(0);
  await expect(page.getByTestId('mobile-insight-correlation-note')).toBeVisible();
  await expect(lead.getByTestId('insight-maturity-badge')).toBeVisible();
  await expect(page.getByTestId('insight-stage-meta')).toHaveCount(0);

  const toolbarPrecedesLead = await page.evaluate(() => {
    const leadNode = document.querySelector('[data-testid="mobile-insight-lead"]');
    const toolbarNode = document.querySelector('[data-testid="insights-findings-toolbar"]');
    return Boolean(leadNode && toolbarNode && toolbarNode.compareDocumentPosition(leadNode) & 4);
  });
  expect(toolbarPrecedesLead).toBe(true);
  await expect(findingsToolbar).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('430px shows the correlation matrix inline alongside findings and analytics', async ({
  page,
}) => {
  await page.setViewportSize({ width: 430, height: 932 });
  await installInsightsApiMock(page);
  await page.goto('/insights');

  // #571: the matrix is prominent inline — not hidden behind a tab. The top
  // insight (mobile lead) stays visible alongside it.
  await expect(page.getByTestId('insight-matrix')).toBeVisible();
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible();

  await page.getByTestId('insights-filter-tab-symptoms').tap();
  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  await expect(page.getByTestId('insights-analytics-panel')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Patterns', exact: true })).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('390px context filter surfaces early work-context insight without overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installInsightsApiMock(page, { includeContextInsight: true });
  await page.goto('/insights');

  await expect(page.getByTestId('insights-findings-toolbar')).toBeVisible({ timeout: 30_000 });
  await page.getByTestId('insights-filter-tab-context').tap();

  const lead = page.getByTestId('mobile-insight-lead');
  await expect(lead).toBeVisible({ timeout: 30_000 });
  await expect(lead.getByTestId('insight-card-title')).toContainText(/Mood -> Office/i);
  await expect(lead).toContainText(/Office days currently sit above/i);
  await expect(page.getByTestId('mobile-insights-more')).toHaveCount(0);

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('desktop preserves the existing analysis-first composition', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installInsightsApiMock(page);
  await page.goto('/insights');

  await expect(page.getByTestId('mobile-insight-lead')).toHaveCount(0);
  await expect(page.getByTestId('insight-stage-header')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('insight-feed')).toBeVisible();
  await expect(page.getByTestId('insight-card')).toHaveCount(4);

  // #571: matrix shows inline on desktop too — no tab toggle.
  await expect(page.getByTestId('insight-matrix')).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});
