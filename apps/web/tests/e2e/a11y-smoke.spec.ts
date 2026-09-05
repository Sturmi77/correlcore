import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

/**
 * Accessibility smoke on the three critical mocked-API routes.
 * Runs with `pnpm test:e2e:smoke` (CI) — serious/critical axe violations fail.
 */

const user = {
  id: '00000000-0000-4000-8000-0000000000a1',
  email: 'a11y-smoke@example.test',
  display_name: 'A11y Smoke',
  is_verified: true,
};

const now = '2026-09-05T10:00:00Z';
const APP_READY_TIMEOUT_MS = 60_000;

test.setTimeout(APP_READY_TIMEOUT_MS);

async function installA11yApi(page: Page, authenticated: boolean) {
  let auth = authenticated;

  await page.addInitScript(() => {
    window.localStorage.setItem('correlcore-locale', 'en');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    const method = request.method();
    const json = (status: number, body: unknown) =>
      route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify(body),
      });

    if (path === '/auth/me' && method === 'GET') {
      return auth ? json(200, user) : json(401, { detail: 'Not authenticated' });
    }
    if (path === '/auth/login' && method === 'POST') {
      auth = true;
      return json(200, {
        access_token: 'a11y-access-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }
    if (path === '/entries' && method === 'GET') {
      return json(200, []);
    }
    if (path === '/insights' && method === 'GET') {
      return json(200, []);
    }
    if (path === '/insights/maturity' && method === 'GET') {
      return json(200, {
        phase: 'developing',
        entry_count: 12,
        next_phase: 'robust',
        entries_to_next: 18,
      });
    }
    if (path === '/user/preferences' && method === 'GET') {
      return json(200, {
        user_id: user.id,
        analytics_enabled: true,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        onboarding_maturity_intro_seen: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: ['phase-developing'],
        last_seen_insight_at: null,
        created_at: now,
        updated_at: now,
      });
    }
    if (path === '/user/profile' && method === 'GET') {
      return json(200, {
        user_id: user.id,
        sleep_hours_typical: null,
        work_context_typical: 'office',
        sport_frequency: null,
        insight_curiosity: null,
        created_at: now,
        updated_at: now,
      });
    }
    if (path === '/stats/dashboard' && method === 'GET') {
      return json(200, {
        entry_count: 0,
        streak_days: 0,
        mood_avg_7d: null,
        latest_entry_date: null,
      });
    }
    return json(200, {});
  });
}

async function expectNoCriticalAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === 'critical' || v.impact === 'serious'
  );
  expect(blocking, JSON.stringify(blocking, null, 2)).toEqual([]);
}

test('login page has no serious axe violations', async ({ page }) => {
  await installA11yApi(page, false);
  await page.goto('/auth/login');
  await expect(page.getByRole('heading', { name: /sign in|anmelden/i })).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expectNoCriticalAxeViolations(page);
});

test('home / entry sheet has no serious axe violations', async ({ page }) => {
  await installA11yApi(page, true);
  await page.goto('/entries/new');
  await expect(page.getByTestId('entry-sheet')).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expectNoCriticalAxeViolations(page);
});

test('insights route has no serious axe violations', async ({ page }) => {
  await installA11yApi(page, true);
  await page.goto('/insights');
  await expect(page.locator('h1').first()).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expectNoCriticalAxeViolations(page);
});
