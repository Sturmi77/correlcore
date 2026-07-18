/**
 * GDPR self-service E2E — M9 Sprint 1
 *
 * Covers Art. 17 account deletion, Art. 20 ZIP export, Art. 21 analytics opt-out,
 * and in-app privacy policy link. Uses mocked API routes (no live backend).
 */
import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000201',
  email: 'gdpr-self-service@example.test',
  display_name: 'GDPR Self Service',
  is_verified: true,
};

const APP_READY_TIMEOUT_MS = 60_000;

type ApiWrite = {
  method: string;
  path: string;
  body: unknown;
};

type GdprApiState = {
  authenticated: boolean;
  analyticsEnabled: boolean;
  writes: ApiWrite[];
};

async function installGdprApi(page: Page, options?: { analyticsEnabled?: boolean }) {
  const state: GdprApiState = {
    authenticated: true,
    analyticsEnabled: options?.analyticsEnabled ?? true,
    writes: [],
  };

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
      return state.authenticated ? json(200, user) : json(401, { detail: 'Not authenticated' });
    }

    if (path === '/auth/logout' && method === 'POST') {
      state.authenticated = false;
      return json(200, { message: 'Logged out' });
    }

    if (path === '/user/preferences' && method === 'GET') {
      return json(200, {
        user_id: user.id,
        analytics_enabled: state.analyticsEnabled,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        onboarding_maturity_intro_seen: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
      });
    }

    if (path === '/user/preferences' && method === 'PATCH') {
      const body = request.postDataJSON() as { analytics_enabled?: boolean };
      if (typeof body.analytics_enabled === 'boolean') {
        state.analyticsEnabled = body.analytics_enabled;
      }
      state.writes.push({ method, path, body });
      return json(200, {
        user_id: user.id,
        analytics_enabled: state.analyticsEnabled,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        onboarding_maturity_intro_seen: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: '2026-07-01T00:00:00Z',
        updated_at: '2026-07-01T00:00:00Z',
      });
    }

    if (path === '/user/me' && method === 'DELETE') {
      const body = request.postDataJSON();
      state.writes.push({ method, path, body });
      state.authenticated = false;
      return route.fulfill({ status: 204, body: '' });
    }

    if (path === '/user/export' && method === 'GET') {
      state.writes.push({ method, path, body: null });
      const zipBytes = Buffer.from('PK\x03\x04mock-gdpr-export');
      return route.fulfill({
        status: 200,
        contentType: 'application/zip',
        headers: {
          'Content-Disposition': 'attachment; filename="correlcore-export-2026-07-11.zip"',
        },
        body: zipBytes,
      });
    }

    if (path === '/dev/info' && method === 'GET') {
      return json(404, { detail: 'disabled' });
    }

    return json(404, { detail: `Unhandled GDPR API route: ${method} ${path}` });
  });

  return state;
}

test.describe.configure({ mode: 'serial' });

test.setTimeout(APP_READY_TIMEOUT_MS);

test('privacy policy is linked from settings and renders sections', async ({ page }) => {
  await installGdprApi(page);
  await page.goto('/settings');

  await expect(page.getByTestId('settings-privacy-policy')).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await page.getByTestId('settings-privacy-policy').click();

  await expect(page).toHaveURL(/\/privacy$/);
  await expect(page.getByTestId('privacy-section-controller')).toBeVisible();
  await expect(page.getByTestId('privacy-section-rights')).toBeVisible();
});

test('ZIP export triggers GET /user/export', async ({ page }) => {
  const api = await installGdprApi(page);
  await page.goto('/settings');

  await expect(page.getByTestId('settings-section-export')).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await page.getByRole('button', { name: /download gdpr zip/i }).click();

  await expect
    .poll(() => api.writes.some((write) => write.method === 'GET' && write.path === '/user/export'))
    .toBe(true);
});

test('analytics opt-out sends PATCH /user/preferences', async ({ page }) => {
  const api = await installGdprApi(page, { analyticsEnabled: true });
  await page.goto('/settings');

  const toggle = page.getByTestId('analytics-toggle');
  await expect(toggle).toBeVisible({ timeout: APP_READY_TIMEOUT_MS });
  await expect(toggle).toBeChecked();

  await toggle.uncheck();

  await expect
    .poll(() =>
      api.writes.some(
        (write) =>
          write.method === 'PATCH' &&
          write.path === '/user/preferences' &&
          (write.body as { analytics_enabled?: boolean }).analytics_enabled === false
      )
    )
    .toBe(true);
  await expect(toggle).not.toBeChecked();
});

test('account deletion confirms password and clears session', async ({ page }) => {
  const api = await installGdprApi(page);
  await page.goto('/settings');

  await page.getByTestId('settings-delete-account').click({ timeout: APP_READY_TIMEOUT_MS });
  await expect(page.getByTestId('settings-delete-dialog')).toBeVisible();

  await page.getByTestId('settings-delete-password').fill('CorrectHorse123!');
  await page.getByTestId('settings-delete-confirm').click();

  await expect
    .poll(() =>
      api.writes.some(
        (write) =>
          write.method === 'DELETE' &&
          write.path === '/user/me' &&
          (write.body as { password?: string }).password === 'CorrectHorse123!'
      )
    )
    .toBe(true);

  await expect(page).toHaveURL(/\/?$/);
});
