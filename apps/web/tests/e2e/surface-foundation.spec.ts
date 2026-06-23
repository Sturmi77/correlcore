import { expect, test, type Page } from '@playwright/test';
import { BASELINE_VIEWPORTS, DESKTOP_SHELL_BREAKPOINT_PX } from '../../src/lib/ui/surfaceContract';

const user = {
  id: '00000000-0000-4000-8000-000000000099',
  email: 'surface-foundation@example.test',
  display_name: 'Surface Foundation',
  is_verified: true,
};

async function installShellMock(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
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
        detail: `Unhandled shell mock route: ${request.method()} ${path}`,
      }),
    });
  });
}

for (const [name, viewport] of Object.entries(BASELINE_VIEWPORTS)) {
  test(`${name} viewport follows the shared shell contract`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await installShellMock(page);
    await page.goto('/settings');

    const nav = page.getByRole('navigation');
    const main = page.locator('#main-content');
    await expect(nav).toBeVisible({ timeout: 15_000 });
    await expect(main).toBeVisible({ timeout: 15_000 });
    await expect(nav.getByRole('link')).toHaveCount(4);

    const [navBox, mainBox, overflow] = await Promise.all([
      nav.boundingBox(),
      main.boundingBox(),
      page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
    ]);

    expect(navBox).not.toBeNull();
    expect(mainBox).not.toBeNull();
    expect(overflow).toBeLessThanOrEqual(0);

    if (viewport.width < DESKTOP_SHELL_BREAKPOINT_PX) {
      expect(navBox!.y).toBeGreaterThan(mainBox!.y);
    } else {
      expect(navBox!.x).toBeLessThan(mainBox!.x);
      expect(Math.abs(navBox!.y - mainBox!.y)).toBeLessThanOrEqual(1);
    }

    for (const link of await nav.getByRole('link').all()) {
      const box = await link.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });
}
