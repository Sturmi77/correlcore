import { expect, test } from '@playwright/test';
import { installInsightsApiMock } from './helpers/insightsApiMock';

test.use({
  viewport: { width: 390, height: 844 },
  hasTouch: true,
});

test('M7 insights mobile mock flow supports touch interactions', async ({ page }) => {
  test.setTimeout(90_000);
  // The symptom/co-occurrence blocks are optional sections (Phase 6 / D5 slim default);
  // this flow exercises them, so the saved layout enables every section.
  await installInsightsApiMock(page, { allSections: true });

  await page.goto('/insights');
  await expect(page.getByTestId('insights-analysis-toolbar')).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('mobile-insight-lead')).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByTestId('mobile-insight-lead').getByTestId('insight-maturity-badge')
  ).toBeVisible();
  await expect(
    page.getByTestId('mobile-insight-lead').getByTestId('insight-stage-meta')
  ).toHaveCount(0);

  await expect(
    page
      .getByTestId('mobile-insights-more')
      .getByText(/Headache/i)
      .first()
  ).toBeVisible();

  // #571: with the section enabled the correlation matrix is inline — no tab toggle.
  await expect(page.getByTestId('insight-matrix')).toBeVisible();

  await page
    .getByRole('heading', { name: 'Symptoms in insights', exact: true })
    .scrollIntoViewIfNeeded();
  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();

  await expect(page.getByTestId('new-insights-modal')).toHaveCount(0);
  await page.getByRole('button', { name: '90D' }).tap();
  await expect(page.getByRole('button', { name: '90D' })).toHaveAttribute('aria-pressed', 'true');
  await expect(
    page.getByRole('heading', { name: 'Symptoms in insights', exact: true })
  ).toBeVisible();

  await page.getByRole('heading', { name: 'Patterns', exact: true }).scrollIntoViewIfNeeded();
  await page.getByTestId('symptom-cooccurrence-cell').first().tap();
  await expect(page.getByTestId('symptom-cooccurrence-detail-sheet')).toBeVisible();
  await page.getByTestId('symptom-cooccurrence-detail-close').tap();
  const tagCooccurrenceCell = page
    .getByRole('gridcell', {
      // Tag pairs read "A and B: both on N of M days ..." (symptom pairs say "together on").
      name: /^(Caffeine and Walk|Walk and Caffeine|Meetings and Walk|Walk and Meetings|Deep work and Walk|Walk and Deep work): both on/i,
    })
    .first();
  await tagCooccurrenceCell.scrollIntoViewIfNeeded();
  await tagCooccurrenceCell.evaluate((element) => {
    (element as HTMLElement).click();
  });
  await expect(page.getByTestId('cooccurrence-entry-sheet')).toBeVisible();
});
