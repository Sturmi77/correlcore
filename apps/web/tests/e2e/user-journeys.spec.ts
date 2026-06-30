/**
 * User journey E2E — workflow regression for W1 (auth), W2 (onboarding),
 * W3 (daily entry), W5–W7 (insights/trends/habits) at key maturity phases.
 *
 * Closes the auth/onboarding state-matrix gap noted in FRONTEND_STATUS.md.
 * Run: pnpm --filter @correlcore/web exec playwright test tests/e2e/user-journeys.spec.ts
 */
import { expect, test, type Page } from '@playwright/test';

const APP_READY_TIMEOUT_MS = 60_000;

type JourneyProfile = 'new_user' | 'week_user' | 'month_user';

const users = {
  new: {
    id: '00000000-0000-4000-8000-000000000101',
    email: 'journey-new@example.test',
    display_name: 'Journey New',
    is_verified: true,
  },
  week: {
    id: '00000000-0000-4000-8000-000000000102',
    email: 'journey-week@example.test',
    display_name: 'Journey Week',
    is_verified: true,
  },
  month: {
    id: '00000000-0000-4000-8000-000000000103',
    email: 'journey-month@example.test',
    display_name: 'Journey Month',
    is_verified: true,
  },
} as const;

const entryId = '10000000-0000-4000-8000-000000000101';
const habitTagId = '20000000-0000-4000-8000-000000000201';
const now = '2026-06-30T10:00:00Z';

function makeEntries(count: number, userId: string) {
  return Array.from({ length: count }, (_, index) => {
    const day = String(index + 1).padStart(2, '0');
    return {
      id: `entry-${index}`,
      user_id: userId,
      entry_date: `2026-06-${day}`,
      slot: 'day' as const,
      mood_score: 3 + (index % 2),
      energy: 3,
      stress: 2,
      cycle_day: null,
      source: 'manual',
      work_context: 'homeoffice',
      note: null,
      created_at: now,
      updated_at: now,
    };
  });
}

function maturityForProfile(profile: JourneyProfile) {
  if (profile === 'new_user') {
    return {
      phase: 'collecting',
      phase_index: 1,
      current_entries: 0,
      next_phase_at: 7,
      next_phase_label: 'First Patterns',
      entries_until_next: 7,
      user_message_key: 'maturity.collecting.message',
    };
  }
  if (profile === 'week_user') {
    return {
      phase: 'early_patterns',
      phase_index: 2,
      current_entries: 9,
      next_phase_at: 14,
      next_phase_label: 'Provisional',
      entries_until_next: 5,
      user_message_key: 'maturity.early_patterns.message',
    };
  }
  return {
    phase: 'robust',
    phase_index: 4,
    current_entries: 32,
    next_phase_at: null,
    next_phase_label: null,
    entries_until_next: null,
    user_message_key: 'maturity.robust.message',
  };
}

function sampleInsight(userId: string, profile: JourneyProfile) {
  if (profile === 'new_user') return [];
  return [
    {
      id: '30000000-0000-4000-8000-000000000001',
      user_id: userId,
      insight_type: 'weekday_pattern',
      tier: profile === 'week_user' ? 'early' : 'robust',
      metric: 'mood_score',
      subject_type: 'weekday',
      subject_id: null,
      subject_label: 'Friday',
      effect_size: 0.55,
      confidence: profile === 'week_user' ? 0.42 : 0.78,
      sample_n: profile === 'week_user' ? 9 : 32,
      statement: 'Fridays currently line up with higher mood than your overall average.',
      flags: { causal_claim: false },
      payload: {},
      generated_for_date: '2026-06-30',
      generated_at: now,
      created_at: now,
      updated_at: now,
    },
  ];
}

async function installJourneyApi(
  page: Page,
  options: {
    profile: JourneyProfile;
    authenticated?: boolean;
  }
) {
  const { profile } = options;
  let authenticated = options.authenticated ?? true;
  let onboardingCompleted = profile !== 'new_user';
  const user =
    profile === 'new_user' ? users.new : profile === 'week_user' ? users.week : users.month;
  const entryCount =
    profile === 'new_user' ? 0 : profile === 'week_user' ? 9 : 32;
  const entries = makeEntries(entryCount, user.id);
  const writes: string[] = [];

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

    if (path === '/auth/register' && method === 'POST') {
      writes.push('POST /auth/register');
      return json(202, { detail: 'Check your email' });
    }

    if (path === '/auth/verify-email' && method === 'POST') {
      writes.push('POST /auth/verify-email');
      return json(200, { detail: 'Email verified' });
    }

    if (path === '/auth/login' && method === 'POST') {
      authenticated = true;
      writes.push('POST /auth/login');
      return json(200, {
        access_token: 'journey-access-token',
        token_type: 'bearer',
        expires_in: 900,
        user,
      });
    }

    if (path === '/user/preferences' && method === 'GET') {
      return json(200, {
        user_id: user.id,
        analytics_enabled: true,
        onboarding_retro_completed: onboardingCompleted,
        onboarding_profile_completed: onboardingCompleted,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: now,
        updated_at: now,
      });
    }

    if (path === '/user/preferences' && method === 'PATCH') {
      const body = request.postDataJSON() as { onboarding_retro_completed?: boolean };
      if (body.onboarding_retro_completed !== undefined) {
        onboardingCompleted = body.onboarding_retro_completed;
      }
      return json(200, {
        user_id: user.id,
        analytics_enabled: true,
        onboarding_retro_completed: onboardingCompleted,
        onboarding_profile_completed: onboardingCompleted,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        last_seen_insight_at: null,
        created_at: now,
        updated_at: now,
      });
    }

    if (path.startsWith('/dashboard/summary')) {
      return json(200, {
        entry_count: entryCount,
        insight_tier: entryCount >= 14 ? 'developing' : 'none',
        confidence_score: entryCount >= 7 ? 0.5 : 0,
      });
    }

    if (path === '/onboarding/tag-suggestions' && method === 'GET') {
      return json(200, {
        groups: [
          {
            category: 'sport',
            suggestions: [
              {
                slug: 'running',
                name: 'Running',
                category: 'sport',
                icon: null,
                color: null,
              },
            ],
          },
        ],
      });
    }

    if (path === '/onboarding/complete' && method === 'POST') {
      writes.push('POST /onboarding/complete');
      onboardingCompleted = true;
      return json(200, {
        created_tags: [],
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
      });
    }

    if (path === '/entries' && method === 'GET') {
      return json(200, entries);
    }

    if (path === '/entries' && method === 'POST') {
      writes.push('POST /entries');
      const body = request.postDataJSON();
      return json(201, {
        id: entryId,
        user_id: user.id,
        entry_date: body.entry_date,
        slot: body.slot ?? 'day',
        mood_score: body.mood_score,
        energy: body.energy,
        stress: body.stress,
        cycle_day: null,
        source: 'manual',
        work_context: body.work_context,
        note: body.note ?? null,
        created_at: now,
        updated_at: now,
      });
    }

    if (path === `/entries/${entryId}` && method === 'PATCH') {
      writes.push(`PATCH /entries/${entryId}`);
      return json(200, {});
    }

    if (path === `/entries/${entryId}/tags` && method === 'PUT') return json(200, []);
    if (path === `/entries/${entryId}/symptoms` && method === 'PUT') return json(200, []);
    if (path === `/entries/${entryId}/tags` && method === 'GET') return json(200, []);
    if (path === `/entries/${entryId}/symptoms` && method === 'GET') return json(200, []);

    if (path === '/entries/delta' && method === 'GET') {
      return json(200, {
        today: null,
        previous: null,
        delta: { mood: null, energy: null, stress: null },
        shared_tags: [],
      });
    }

    if ((path === '/tags/default' || path === '/tags') && method === 'GET') {
      const tags = [
        {
          id: 'tag-focus',
          user_id: user.id,
          slug: 'focus',
          name: 'Focus',
          category: 'work',
          icon: null,
          color: null,
          is_default: false,
          is_hidden: false,
          habit_type: 'none' as const,
          target_frequency: null as number | null,
          created_at: now,
          updated_at: now,
        },
        ...(profile === 'month_user'
          ? [
              {
                id: habitTagId,
                user_id: user.id,
                slug: 'meditation',
                name: 'Meditation',
                category: 'health',
                icon: null,
                color: null,
                is_default: false,
                is_hidden: false,
                habit_type: 'build' as const,
                target_frequency: 5,
                created_at: now,
                updated_at: now,
              },
            ]
          : []),
      ];
      return json(200, tags);
    }

    if ((path === '/symptoms/default' || path === '/symptoms') && method === 'GET') {
      return json(200, []);
    }

    if (path.startsWith('/entries/stats/timeseries')) {
      return json(200, {
        range: url.searchParams.get('range') ?? 'week',
        points: entries.slice(-7).map((entry) => ({
          period_start: entry.entry_date,
          period_end: entry.entry_date,
          entry_count: 1,
          mood_avg: entry.mood_score,
          energy_avg: entry.energy,
          stress_avg: entry.stress,
        })),
      });
    }

    if (path.startsWith('/entries/stats/tags')) {
      return json(200, { start_date: '2026-06-01', end_date: '2026-06-30', tags: [] });
    }

    if (path.startsWith('/entries/stats/symptoms')) {
      return json(200, { start_date: '2026-06-01', end_date: '2026-06-30', symptoms: [] });
    }

    if (path.startsWith('/entries/stats/streak')) {
      return json(200, {
        current_streak: entryCount > 0 ? Math.min(entryCount, 7) : 0,
        longest_streak: entryCount,
        total_entry_days: entryCount,
        last_entry_date: entryCount > 0 ? '2026-06-30' : null,
        as_of: '2026-06-30',
      });
    }

    if (path.startsWith('/insights/tag-cooccurrence')) {
      return json(200, { range: 'month', cells: [], tags: [] });
    }

    if (path.startsWith('/insights/tag-clusters')) {
      return json(200, { clusters: [] });
    }

    if (path.startsWith('/insights/symptom-tag-cooccurrence')) {
      return json(200, { range: 'month', cells: [], symptoms: [], tags: [] });
    }

    if (path === '/insights' && method === 'GET') {
      const maturity = maturityForProfile(profile);
      return json(200, {
        insight_maturity: maturity,
        insights: sampleInsight(user.id, profile),
      });
    }

    if (path === '/insights/latest' && method === 'GET') {
      const maturity = maturityForProfile(profile);
      return json(200, {
        insight_maturity: maturity,
        insights: sampleInsight(user.id, profile),
      });
    }

    if (path === '/habits' && method === 'GET') {
      if (profile !== 'month_user') return json(200, { habits: [] });
      return json(200, {
        habits: [
          {
            tag_id: habitTagId,
            habit_type: 'build',
            target_frequency: 5,
            window: 28,
            start_date: '2026-06-03',
            end_date: '2026-06-30',
            days_tracked: 18,
            days_total: 28,
            target_days: 20,
            adherence_rate: 0.64,
            correlation_score: 0.31,
            correlation_metric: 'mood_score',
          },
        ],
      });
    }

    if (path === '/dev/info' && method === 'GET') return json(404, { detail: 'disabled' });

    return json(404, { detail: `Unhandled journey route: ${method} ${path}` });
  });

  return { writes, user };
}

test.describe.configure({ mode: 'serial' });

test.describe('W1 Account & Vertrauen', () => {
  test('registration reaches check-email', async ({ page }) => {
    await installJourneyApi(page, { profile: 'new_user', authenticated: false });
    await page.goto('/auth/register');

    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await page.locator('input[type="email"]').fill(users.new.email);
    await page.locator('input[type="password"]').fill('CorrectHorse123!');
    await page.locator('button[type="submit"]').click();

    await expect(page).toHaveURL(/\/auth\/check-email/);
    await expect(page.getByRole('heading', { name: 'Check your inbox' })).toBeVisible();
  });

  test('email verification requires explicit confirm', async ({ page }) => {
    await installJourneyApi(page, { profile: 'new_user', authenticated: false });
    await page.goto('/auth/verify-email?token=journey-test-token');

    await expect(page.getByRole('button', { name: 'Verify email' })).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await page.getByRole('button', { name: 'Verify email' }).click();
    await expect(page.getByRole('link', { name: /sign in|log in/i })).toBeVisible();
  });
});

test.describe('W2 Cold Start / Onboarding @390', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('new user is redirected from home to guided onboarding', async ({ page }) => {
    await installJourneyApi(page, { profile: 'new_user' });
    await page.goto('/');

    await expect(page).toHaveURL(/\/onboarding$/, { timeout: APP_READY_TIMEOUT_MS });
    await expect(page.getByRole('heading', { name: 'Set up your tracking' })).toBeVisible();
  });

  test('onboarding skip completes and returns to home CTA', async ({ page }) => {
    const api = await installJourneyApi(page, { profile: 'new_user' });
    await page.goto('/onboarding');

    await page.getByRole('button', { name: 'Skip', exact: true }).click();
    await expect(page).toHaveURL('/', { timeout: APP_READY_TIMEOUT_MS });
    await expect(page.getByTestId('home-cta')).toBeVisible();
    expect(api.writes).toContain('POST /onboarding/complete');
  });

  test('onboarding tag flow reaches start tracking', async ({ page }) => {
    const api = await installJourneyApi(page, { profile: 'new_user' });
    await page.goto('/onboarding');

    await page.getByRole('button', { name: 'Continue', exact: true }).click();
    await page.getByRole('button', { name: 'Running' }).click();
    await page.getByRole('button', { name: 'Continue', exact: true }).click();
    await page.getByRole('button', { name: 'Start tracking' }).click();

    await expect(page).toHaveURL('/', { timeout: APP_READY_TIMEOUT_MS });
    expect(api.writes).toContain('POST /onboarding/complete');
  });
});

test.describe('W3 Tägliche Eingabe', () => {
  test('mobile home CTA opens entry sheet and autosaves', async ({ page }) => {
    test.setTimeout(90_000);
    const api = await installJourneyApi(page, { profile: 'week_user' });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('/');

    await page.getByTestId('home-cta').click();
    await expect(page.getByTestId('entry-sheet')).toBeVisible({ timeout: APP_READY_TIMEOUT_MS });

    await page.getByRole('button', { name: 'Increase mood' }).click();
    await expect
      .poll(() => api.writes.some((write) => write === 'POST /entries'))
      .toBe(true);
    await expect(page.locator('form.entry-form')).toHaveAttribute('data-autosave-status', 'saved');

    await page.getByTestId('entry-sheet-close').click();
    await expect(page.getByTestId('entry-sheet')).toHaveCount(0);
  });

  test('desktop entry page keeps optional details expanded', async ({ page }) => {
    await installJourneyApi(page, { profile: 'week_user' });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/entries/new');

    await expect(page.getByRole('heading', { name: 'Log your day' })).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await expect(page.locator('#entry-section-tags')).toBeVisible();
  });
});

test.describe('W5 Erste Erkenntnis', () => {
  test('collecting phase shows home brief without insight card', async ({ page }) => {
    await installJourneyApi(page, { profile: 'new_user' });
    await page.setViewportSize({ width: 390, height: 844 });

    // Skip onboarding to inspect home collecting state
    await page.goto('/onboarding');
    await page.getByRole('button', { name: 'Skip', exact: true }).click();
    await expect(page).toHaveURL('/');

    await expect(page.getByTestId('home-daily-brief')).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await expect(page.getByTestId('home-cta')).toBeVisible();
  });

  test('week user sees insight statement on insights', async ({ page }) => {
    await installJourneyApi(page, { profile: 'week_user' });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/insights');

    await expect(page.getByTestId('insight-stage-header')).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await expect(page.getByText(/fridays currently line up/i)).toBeVisible();
    await expect(page.getByTestId('insight-maturity-badge')).toHaveAttribute(
      'data-phase',
      'early_patterns'
    );
  });
});

test.describe('W6–W7 Analyse & Habits', () => {
  test('week user trends compare panel renders', async ({ page }) => {
    await installJourneyApi(page, { profile: 'week_user' });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/trends');

    await expect(page.getByRole('heading', { name: 'Trends' })).toBeVisible({
      timeout: APP_READY_TIMEOUT_MS,
    });
    await expect(page.getByTestId('trends-compare-panel')).toBeVisible();
  });

  test('month user habits tab shows adherence panel', async ({ page }) => {
    await installJourneyApi(page, { profile: 'month_user' });
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/trends');

    await page.getByTestId('trends-tab-habits').click();
    await expect(page.getByTestId('habits-panel')).toBeVisible({ timeout: APP_READY_TIMEOUT_MS });
    await expect(page.getByTestId(`habit-row-${habitTagId}`)).toBeVisible();
  });

  test('month user insights use robust maturity phase', async ({ page }) => {
    await installJourneyApi(page, { profile: 'month_user' });
    await page.goto('/insights');

    await expect(page.getByTestId('insight-maturity-badge')).toHaveAttribute(
      'data-phase',
      'robust',
      { timeout: APP_READY_TIMEOUT_MS }
    );
  });
});
