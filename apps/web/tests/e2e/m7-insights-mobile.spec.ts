import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000007',
  email: 'm7-mobile@example.com',
  display_name: 'M7 Mobile',
  is_verified: true,
};

async function installM7MockMode(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
    window.localStorage.setItem('dev_mode_enabled', 'true');
    window.localStorage.setItem('dev_force_viz', 'true');
    window.localStorage.setItem('cc_insights_symptoms', 'true');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');

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
      body: JSON.stringify({ detail: `Unhandled M7 mock API route: ${request.method()} ${path}` }),
    });
  });
}

test.use({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});

test('M7 insights mobile mock flow supports touch interactions', async ({ page }) => {
  await installM7MockMode(page);

  await page.goto('/insights');
  await expect(page.getByText(/Phase 4 of 4: Robust Insights/i)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Insights' })).toHaveAttribute(
    'aria-current',
    'page'
  );

  await page.getByTestId('insight-feed-tab-symptoms').tap();
  await expect(page.getByText(/Headache.*mood_score/i).first()).toBeVisible();

  await page.getByRole('button', { name: /matrix/i }).tap();
  await expect(page.getByText(/Correlation Matrix/i)).toBeVisible();
  await page.getByRole('button', { name: /findings/i }).tap();

  const symptomToggle = page.locator('label', { hasText: /blend in symptoms/i }).locator('input');
  await symptomToggle.uncheck();
  await expect(symptomToggle).not.toBeChecked();
  await symptomToggle.check();
  await expect(symptomToggle).toBeChecked();

  await page.getByRole('heading', { name: 'Patterns', exact: true }).scrollIntoViewIfNeeded();
  await page.getByRole('button', { name: '1Y' }).tap();
  await expect(page.getByRole('button', { name: '1Y' })).toHaveAttribute('aria-pressed', 'true');
  await page
    .getByRole('gridcell', { name: /Focus work and Walk together/i })
    .first()
    .tap();
  await expect(page.getByTestId('cooccurrence-entry-sheet')).toBeVisible();
});
