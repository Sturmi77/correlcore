import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000044',
  email: 'supporting-flows@example.test',
  display_name: 'Supporting Flows',
  is_verified: true,
};

async function installSupportingFlowApi(page: Page) {
  await page.addInitScript(() => localStorage.setItem('correlcore-locale', 'en'));
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (path === '/auth/me') return json(200, user);
    if (path === '/user/preferences') {
      return json(200, {
        user_id: user.id,
        analytics_enabled: true,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: '2026-06-01T00:00:00Z',
        updated_at: '2026-06-01T00:00:00Z',
      });
    }
    if (path === '/dev/info') return json(404, { detail: 'disabled' });
    if (path === '/symptoms') {
      return json(200, [
        {
          id: 'default-fatigue',
          user_id: null,
          slug: 'fatigue',
          name: 'Fatigue',
          icon: null,
          is_default: true,
          created_at: '2026-06-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
        },
        {
          id: 'custom-aura',
          user_id: user.id,
          slug: 'aura',
          name: 'Aura',
          icon: null,
          is_default: false,
          created_at: '2026-06-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
        },
      ]);
    }

    return json(404, { detail: `Unhandled supporting flow: ${request.method()} ${path}` });
  });
}

for (const viewport of [
  { width: 390, height: 844 },
  { width: 430, height: 932 },
]) {
  test(`${viewport.width}px exposes mobile management without horizontal overflow`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await installSupportingFlowApi(page);
    await page.goto('/settings');

    const symptomsLink = page.getByTestId('settings-vocab-symptoms');
    const appLink = page.getByRole('link', { name: 'App & offline' });
    await expect(symptomsLink).toBeVisible({ timeout: 15_000 });
    await expect(appLink).toBeVisible();

    for (const control of [symptomsLink, appLink]) {
      expect((await control.boundingBox())?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    ).toBeLessThanOrEqual(0);

    await symptomsLink.click();
    await expect(page.getByTestId('custom-symptom-row').locator('input').first()).toHaveValue(
      'Aura'
    );
    await expect(page.getByText(/Fatigue/)).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    ).toBeLessThanOrEqual(0);
  });
}

test('connection loss surfaces a global retry state', async ({ context, page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installSupportingFlowApi(page);
  await page.goto('/settings');
  await expect(page.getByTestId('settings-vocab-symptoms')).toBeVisible({
    timeout: 15_000,
  });

  await context.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event('offline')));

  const banner = page.getByTestId('pwa-offline-banner');
  await expect(banner).toBeVisible();
  expect(
    (await banner.getByRole('button', { name: 'Retry' }).boundingBox())?.height ?? 0
  ).toBeGreaterThanOrEqual(44);
});

test('desktop keeps management controls in a dense row', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installSupportingFlowApi(page);
  await page.goto('/settings/symptoms');

  const row = page.getByTestId('custom-symptom-row');
  const input = row.locator('input').first();
  const save = row.getByRole('button', { name: 'Save' });
  const [inputBox, saveBox] = await Promise.all([input.boundingBox(), save.boundingBox()]);
  expect(inputBox).not.toBeNull();
  expect(saveBox).not.toBeNull();
  expect(Math.abs(inputBox!.y - saveBox!.y)).toBeLessThan(50);
});
