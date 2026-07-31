import { expect, test, type Page } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

const user = {
  id: '00000000-0000-4000-8000-000000000001',
  email: 'm4-smoke@example.test',
  display_name: 'M4 Smoke',
  is_verified: true,
};

const now = '2026-05-22T10:00:00Z';
const entryId = '10000000-0000-4000-8000-000000000001';
const APP_READY_TIMEOUT_MS = 60_000;

test.setTimeout(APP_READY_TIMEOUT_MS);

type ApiWrite = {
  method: string;
  path: string;
  body: unknown;
};

async function installSmokeApi(page: Page, options: { authenticated: boolean }) {
  let authenticated = options.authenticated;
  const writes: ApiWrite[] = [];

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
      return authenticated ? json(200, user) : json(401, { detail: 'Not authenticated' });
    }

    if (path === '/auth/login' && method === 'POST') {
      authenticated = true;
      writes.push({ method, path, body: request.postDataJSON() });
      return json(200, {
        access_token: 'smoke-access-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }

    if (path === '/entries' && method === 'GET') {
      return json(200, []);
    }

    if (path === '/entries' && method === 'POST') {
      const body = request.postDataJSON();
      writes.push({ method, path, body });
      return json(201, {
        id: entryId,
        user_id: user.id,
        entry_date: body.entry_date,
        slot: body.slot ?? 'day',
        mood_score: body.mood_score,
        energy: body.energy,
        stress: body.stress,
        source: body.source ?? 'manual',
        work_context: body.work_context,
        note: body.note ?? null,
        created_at: now,
        updated_at: now,
      });
    }

    if (path === `/entries/${entryId}` && method === 'PATCH') {
      const body = request.postDataJSON();
      writes.push({ method, path, body });
      return json(200, {
        id: entryId,
        user_id: user.id,
        entry_date: '2026-05-22',
        slot: 'day',
        mood_score: body.mood_score ?? 4,
        energy: body.energy ?? 3,
        stress: body.stress ?? 3,
        source: 'manual',
        work_context: body.work_context ?? 'homeoffice',
        note: body.note ?? null,
        created_at: now,
        updated_at: now,
      });
    }

    if (path === `/entries/${entryId}/tags` && method === 'PUT') {
      writes.push({ method, path, body: request.postDataJSON() });
      return json(200, []);
    }

    if (path === `/entries/${entryId}/symptoms` && method === 'PUT') {
      writes.push({ method, path, body: request.postDataJSON() });
      return json(200, []);
    }

    if (path === '/entries/delta' && method === 'GET') {
      return json(200, {
        today: null,
        previous: null,
        delta: { mood: null, energy: null, stress: null },
        shared_tags: [],
      });
    }

    if ((path === '/tags/default' || path === '/tags') && method === 'GET') {
      return json(200, []);
    }

    if ((path === '/symptoms/default' || path === '/symptoms') && method === 'GET') {
      return json(200, []);
    }

    if (path === '/entries/stats/timeseries' && method === 'GET') {
      return json(200, {
        range: url.searchParams.get('range') ?? 'week',
        points: [
          {
            period_start: '2026-05-20',
            period_end: '2026-05-20',
            entry_count: 1,
            mood_avg: 4,
            energy_avg: 3,
            stress_avg: 2,
          },
        ],
      });
    }

    if (path === '/entries/stats/tags' && method === 'GET') {
      return json(200, {
        start_date: url.searchParams.get('start_date') ?? '2026-05-16',
        end_date: url.searchParams.get('end_date') ?? '2026-05-22',
        tags: [],
      });
    }

    if (path === '/entries/stats/symptoms' && method === 'GET') {
      return json(200, {
        start_date: url.searchParams.get('start_date') ?? '2026-05-16',
        end_date: url.searchParams.get('end_date') ?? '2026-05-22',
        symptoms: [],
      });
    }

    if (path === '/entries/stats/streak' && method === 'GET') {
      return json(200, {
        current_streak: 3,
        longest_streak: 5,
        total_entry_days: 12,
        last_entry_date: '2026-05-22',
        as_of: '2026-05-22',
      });
    }

    if (path === '/insights/latest' && method === 'GET') {
      return json(200, {
        insight_maturity: {
          phase: 'provisional',
          phase_index: 3,
          current_entries: 18,
          next_phase_at: 30,
          next_phase_label: 'robust',
          entries_until_next: 12,
          user_message_key: 'maturity.provisional.description',
        },
        insights: [
          {
            id: '20000000-0000-4000-8000-000000000001',
            user_id: user.id,
            insight_type: 'weekday_pattern',
            tier: 'developing',
            metric: 'mood_score',
            subject_type: 'weekday',
            subject_id: null,
            subject_label: 'Friday',
            effect_size: 0.7,
            confidence: 0.62,
            sample_n: 18,
            statement: 'Fridays currently line up with higher mood than your overall average.',
            flags: { causal_claim: false },
            payload: {},
            generated_for_date: '2026-05-22',
            generated_at: now,
            created_at: now,
            updated_at: now,
          },
        ],
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

    return json(404, { detail: `Unhandled smoke API route: ${method} ${path}` });
  });

  return { writes };
}

test('anonymous home shows the marketing landing page (#588)', async ({ page }) => {
  await installSmokeApi(page, { authenticated: false });

  await page.goto('/');
  await expect(page.getByTestId('marketing-landing')).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expect(page.getByTestId('landing-cta-login')).toBeVisible();
  await expect(page.getByTestId('app-nav-brand')).toHaveCount(0);
});

test('authenticated landing preview uses ?landing=1 without app nav (#588)', async ({ page }) => {
  await installSmokeApi(page, { authenticated: true });

  await page.goto('/?landing=1');
  await expect(page.getByTestId('marketing-landing')).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expect(page.getByTestId('home-zone-context')).toHaveCount(0);
});

test('login redirects to a protected workflow', async ({ page }) => {
  await installSmokeApi(page, { authenticated: false });

  await page.goto('/auth/login?next=/entries/new');
  await expect(page.getByRole('heading', { name: /sign in|anmelden/i })).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await page.locator('input[type="email"]').fill(user.email);
  await page.locator('input[type="password"]').fill('CorrectHorse123!');
  await page.locator('button[type="submit"]').click();

  await expect(page).toHaveURL(/\/?(\?openEntry=1)?$/);
  await expect(page.getByTestId('entry-sheet')).toBeVisible({ timeout: APP_READY_TIMEOUT_MS });
});

test('entry creation autosaves the core daily metrics', async ({ page }) => {
  const api = await installSmokeApi(page, { authenticated: true });

  await page.goto('/entries/new');
  await expect(page.getByTestId('entry-sheet')).toBeVisible({ timeout: APP_READY_TIMEOUT_MS });

  await page.locator('#entry-mood').evaluate((element) => {
    const input = element as HTMLInputElement;
    input.value = '4';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });

  await expect
    .poll(() => api.writes.some((write) => write.method === 'POST' && write.path === '/entries'))
    .toBe(true);
  await expect(page.locator('form.entry-form')).toHaveAttribute('data-autosave-status', 'saved');
});

test('trends and insights render authenticated analytics surfaces', async ({ page }) => {
  await installSmokeApi(page, { authenticated: true });

  await page.goto('/trends');
  await expect(page.getByRole('heading', { name: /trends/i })).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expect(page.getByTestId('trends-compare-panel')).toBeVisible();
  await expect(page.getByTestId('trends-health-context')).toBeVisible();
  await expect(page.locator('.trends-health__consistency strong').first()).toHaveText('3');

  await page.goto('/insights');
  await expect(page.getByText(/fridays currently line up/i)).toBeVisible({
    timeout: APP_READY_TIMEOUT_MS,
  });
  await expect(page.getByTestId('insight-stage-header')).toHaveAttribute(
    'data-phase',
    'provisional'
  );
  await expect(page.getByTestId('insight-stage-meta')).toBeVisible();
});
