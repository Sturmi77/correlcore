import { expect, test } from '@playwright/test';
import { mockInsights } from '../../src/lib/dev/mockInsights';
import { installInsightsApiMock } from './helpers/insightsApiMock';

test.use({ hasTouch: true });

test('390px prioritizes the strongest signal, confidence, and maturity', async ({ page }) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 390, height: 844 });
  await installInsightsApiMock(page);
  await page.goto('/insights');

  const lead = page.getByTestId('mobile-insight-lead');
  const confidence = page.getByTestId('insight-card-confidence-summary');
  const analysisToolbar = page.getByTestId('insights-analysis-toolbar');

  await expect(analysisToolbar).toBeVisible({ timeout: 60_000 });
  await expect(lead).toBeVisible({ timeout: 30_000 });
  await expect(lead.getByTestId('insight-card-title')).toContainText(/Energy/i);
  await expect(confidence).toBeVisible();
  await expect(page.getByTestId('insight-confidence-score-percent')).toHaveCount(0);
  await expect(page.getByTestId('mobile-insight-lead-disclaimer-btn')).toBeVisible();
  await expect(lead.getByTestId('insight-maturity-badge')).toBeVisible();
  await expect(lead.getByTestId('insight-stage-meta')).toHaveCount(0);
  await expect(page.getByTestId('insight-stage-header')).toBeVisible();

  const toolbarPrecedesLead = await page.evaluate(() => {
    const leadNode = document.querySelector('[data-testid="mobile-insight-lead"]');
    const toolbarNode = document.querySelector('[data-testid="insights-analysis-toolbar"]');
    return Boolean(leadNode && toolbarNode && toolbarNode.compareDocumentPosition(leadNode) & 4);
  });
  expect(toolbarPrecedesLead).toBe(true);
  await expect(analysisToolbar).toBeVisible();

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

  await expect(page.getByTestId('insights-analysis-toolbar')).toBeVisible({ timeout: 30_000 });
  // #571: the matrix is prominent inline above the top insight (mobile lead).
  await expect(page.getByTestId('insight-matrix')).toBeVisible();
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible();
  const matrixBox = await page.getByTestId('insight-matrix').boundingBox();
  const leadBox = await page.getByTestId('mobile-insight-lead').boundingBox();
  expect(matrixBox && leadBox && matrixBox.y < leadBox.y).toBe(true);

  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  await expect(page.getByTestId('insight-section-symptom_analytics')).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Patterns', exact: true })).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});

test('390px surfaces the work-context insight without overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installInsightsApiMock(page, { includeContextInsight: true });
  await page.goto('/insights');

  await expect(page.getByTestId('insights-analysis-toolbar')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText(/Office days currently sit above/i)).toBeVisible();

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

  await expect(page.getByTestId('insights-analysis-toolbar')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('mobile-insight-lead')).toHaveCount(0);
  await expect(page.getByTestId('insight-stage-header')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('insight-feed')).toBeVisible();
  await expect(page.getByTestId('insight-feed').getByTestId('insight-card')).toHaveCount(
    mockInsights.length
  );

  // #571: matrix shows inline on desktop too — no tab toggle.
  await expect(page.getByTestId('insight-matrix')).toBeVisible();

  const layout = await page.evaluate(() => ({
    viewport: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(layout.scrollWidth).toBeLessThanOrEqual(layout.viewport);
});
