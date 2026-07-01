import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000092',
  email: 'mobile-theme@example.test',
  display_name: 'Mobile Theme',
  is_verified: true,
};

const preferences = {
  user_id: user.id,
  analytics_enabled: true,
  onboarding_retro_completed: true,
  onboarding_profile_completed: true,
  dismissed_insight_keys: [] as string[],
  reached_milestone_keys: [] as string[],
  last_seen_insight_at: null as string | null,
  created_at: '2026-06-01T00:00:00Z',
  updated_at: '2026-06-01T00:00:00Z',
};

async function installDarkThemeApi(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
    window.localStorage.setItem('correlcore-theme', 'dark');
    window.localStorage.setItem('dev_mode_enabled', 'true');
    window.localStorage.setItem('dev_force_viz', 'true');
    window.localStorage.setItem('cc_insights_symptoms', 'true');
    document.documentElement.setAttribute('data-theme', 'dark');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1', '');
    const method = request.method();
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (path === '/auth/me' && method === 'GET') return json(200, user);
    if (path === '/auth/refresh' && method === 'POST') {
      return json(200, {
        access_token: 'theme-parity-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }
    if (path === '/user/preferences' && method === 'GET') return json(200, preferences);
    if (path === '/entries' && method === 'GET') return json(200, []);
    if (path === '/tags' && method === 'GET') return json(200, []);
    if (path === '/symptoms' && method === 'GET') return json(200, []);
    if (path.startsWith('/dashboard/summary')) {
      return json(200, { entry_count: 0, insight_tier: 'none', confidence_score: 0 });
    }
    if (path.startsWith('/entries/stats/timeseries')) {
      return json(200, { range: 'week', points: [] });
    }
    if (path.startsWith('/entries/stats/tags')) return json(200, { tags: [] });
    if (path.startsWith('/entries/stats/symptoms')) return json(200, { symptoms: [] });
    if (path.startsWith('/entries/stats/streak')) {
      return json(200, { current_streak: 0, longest_streak: 0, as_of: '2026-06-27' });
    }
    if (path.startsWith('/insights/maturity')) {
      return json(200, {
        phase: 'collecting',
        phase_index: 1,
        current_entries: 3,
        next_phase_at: 7,
        entries_until_next: 4,
        next_phase_label: 'Early patterns',
        user_message_key: 'maturity.collecting.message',
      });
    }
    if (path.startsWith('/insights')) return json(200, []);

    return json(404, { detail: `Unhandled ${method} ${path}` });
  });
}

async function expectDarkShell(page: Page, route: string) {
  const authReady = page.waitForResponse(
    (response) => response.url().includes('/auth/me') && response.ok()
  );
  await page.goto(route);
  await authReady;
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark', { timeout: 30_000 });
  await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible({
    timeout: 30_000,
  });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1
  );
  expect(overflow, `horizontal overflow on ${route}`).toBe(false);
}

test.describe('mobile theme parity @390', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test.beforeEach(async ({ page }) => {
    await installDarkThemeApi(page);
  });

  test('dark theme renders primary mobile routes without shell overflow', async ({ page }) => {
    test.setTimeout(120_000);
    await expectDarkShell(page, '/');
    await expectDarkShell(page, '/?openEntry=1');
    await expectDarkShell(page, '/trends');
    await expectDarkShell(page, '/insights');
    await expectDarkShell(page, '/settings');
  });
});
