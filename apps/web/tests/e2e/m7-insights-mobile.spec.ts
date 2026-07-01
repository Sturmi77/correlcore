import { expect, test } from '@playwright/test';
import { installInsightsApiMock } from './helpers/insightsApiMock';

test.use({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
});

test('M7 insights mobile mock flow supports touch interactions', async ({ page }) => {
  test.setTimeout(60_000);
  await installInsightsApiMock(page);

  await page.goto('/insights');
  await expect(page.getByTestId('insights-view-tabs')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByTestId('mobile-insight-lead').getByTestId('insight-maturity-badge')
  ).toBeVisible();
  await expect(page.getByTestId('insight-stage-meta')).toHaveCount(0);

  await page.getByTestId('insight-feed-tab-symptoms').tap();
  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  await page.getByTestId('insights-view-matrix').tap();
  await expect(page.getByText(/Correlation Matrix/i)).toBeVisible();
  await page.getByTestId('insights-view-findings').tap();
  await page.getByText('Deepen analysis', { exact: true }).tap();

  const symptomToggle = page.locator('label', { hasText: /blend in symptoms/i }).locator('input');
  await symptomToggle.uncheck();
  await expect(symptomToggle).not.toBeChecked();
  await symptomToggle.check();
  await expect(symptomToggle).toBeChecked();

  await page.getByRole('heading', { name: 'Patterns', exact: true }).scrollIntoViewIfNeeded();
  await page.getByTestId('symptom-cooccurrence-cell').first().tap();
  await expect(page.getByTestId('symptom-cooccurrence-detail-sheet')).toBeVisible();
  await page.getByTestId('symptom-cooccurrence-detail-close').tap();
  await page.getByRole('button', { name: '1Y' }).tap();
  await expect(page.getByRole('button', { name: '1Y' })).toHaveAttribute('aria-pressed', 'true');
  const tagCooccurrenceCell = page
    .getByRole('gridcell', { name: /Focus work and Walk together/i })
    .first();
  await tagCooccurrenceCell.scrollIntoViewIfNeeded();
  await tagCooccurrenceCell.evaluate((element) => {
    (element as HTMLElement).click();
  });
  await expect(page.getByTestId('cooccurrence-entry-sheet')).toBeVisible();
});
