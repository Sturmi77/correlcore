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
  await expect(page.getByTestId('insights-findings-toolbar')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByTestId('mobile-insight-lead').getByTestId('insight-maturity-badge')
  ).toBeVisible();
  await expect(page.getByTestId('insight-stage-meta')).toHaveCount(0);

  await page.getByTestId('insights-filter-tab-symptoms').tap();
  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  // #571: correlation matrix is inline & always visible — no tab toggle.
  await expect(page.getByText(/Correlation Matrix/i)).toBeVisible();
  await page.getByTestId('insights-filter-tab-symptoms').tap();
  await page.getByText('Deepen analysis', { exact: true }).tap();

  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();
  await page.getByTestId('insights-filter-tab-mood').tap();
  await expect(page.getByTestId('insights-filter-tab-mood')).toHaveAttribute(
    'aria-selected',
    'true'
  );
  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();
  await page.getByTestId('insights-filter-tab-symptoms').tap();
  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();

  await page.getByRole('heading', { name: 'Patterns', exact: true }).scrollIntoViewIfNeeded();
  await page.getByTestId('symptom-cooccurrence-cell').first().tap();
  await expect(page.getByTestId('symptom-cooccurrence-detail-sheet')).toBeVisible();
  await page.getByTestId('symptom-cooccurrence-detail-close').tap();
  await page.getByRole('button', { name: '90D' }).tap();
  await expect(page.getByRole('button', { name: '90D' })).toHaveAttribute('aria-pressed', 'true');
  const tagCooccurrenceCell = page
    .getByRole('gridcell', { name: /Focus work and Walk together/i })
    .first();
  await tagCooccurrenceCell.scrollIntoViewIfNeeded();
  await tagCooccurrenceCell.evaluate((element) => {
    (element as HTMLElement).click();
  });
  await expect(page.getByTestId('cooccurrence-entry-sheet')).toBeVisible();
});
