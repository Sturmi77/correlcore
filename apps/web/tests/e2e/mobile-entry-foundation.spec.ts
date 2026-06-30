import { expect, test, type Page } from '@playwright/test';

const user = {
  id: '00000000-0000-4000-8000-000000000091',
  email: 'mobile-entry@example.test',
  display_name: 'Mobile Entry',
  is_verified: true,
};

const entryId = '10000000-0000-4000-8000-000000000091';

async function installEntryApi(
  page: Page,
  options: { historical?: boolean; offlineSync?: boolean } = {}
) {
  let failWrites = false;
  const writes: string[] = [];
  const syncWrites: string[] = [];

  await page.addInitScript((offlineSync) => {
    window.localStorage.setItem('correlcore-locale', 'en');
    if (offlineSync) {
      window.localStorage.setItem('cc_offline_sync_enabled', 'true');
    }
  }, options.offlineSync ?? false);

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace('/api/v1', '');
    const method = request.method();
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });

    if (path === '/auth/me' && method === 'GET') return json(200, user);

    if (path === '/entries' && method === 'GET') {
      if (!options.historical) return json(200, []);
      return json(200, [
        {
          id: entryId,
          user_id: user.id,
          entry_date: '2026-01-01',
          slot: 'day',
          mood_score: 3,
          energy: 3,
          stress: 2,
          cycle_day: null,
          source: 'manual',
          work_context: 'office',
          note: 'Historical note',
          created_at: '2026-01-01T12:00:00Z',
          updated_at: '2026-01-01T12:00:00Z',
        },
      ]);
    }

    if (path === '/entries' && method === 'POST') {
      if (failWrites) return route.abort('internetdisconnected');
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
        cycle_day: body.cycle_day ?? null,
        source: 'manual',
        work_context: body.work_context,
        note: body.note ?? null,
        created_at: '2026-06-23T07:00:00Z',
        updated_at: '2026-06-23T07:00:00Z',
      });
    }

    if (path === `/entries/${entryId}` && method === 'PATCH') {
      if (failWrites) return route.abort('internetdisconnected');
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

    if (path === '/sync/push' && method === 'POST') {
      if (failWrites) return route.abort('internetdisconnected');
      syncWrites.push('POST /sync/push');
      return json(200, {
        cursor: 'cursor-e2e',
        applied: 1,
        skipped: 0,
        conflicts: [],
        idempotent_replay: false,
      });
    }

    if (path === '/sync/pull' && method === 'GET') {
      return json(200, {
        cursor: 'cursor-e2e',
        changes: [],
        has_more: false,
        server_time: '2026-06-30T12:00:00.000Z',
      });
    }

    if ((path === '/tags/default' || path === '/tags') && method === 'GET') {
      return json(200, [
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
          habit_type: 'none',
          target_frequency: null,
          created_at: '2026-06-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
        },
      ]);
    }

    if ((path === '/symptoms/default' || path === '/symptoms') && method === 'GET') {
      return json(200, [
        {
          id: 'symptom-headache',
          user_id: null,
          slug: 'headache',
          name: 'Headache',
          icon: null,
          is_default: true,
          created_at: '2026-06-01T00:00:00Z',
          updated_at: '2026-06-01T00:00:00Z',
        },
      ]);
    }

    return json(404, { detail: `Unhandled entry mock route: ${method} ${path}` });
  });

  return {
    writes,
    syncWrites,
    setOffline(value: boolean) {
      failWrites = value;
    },
  };
}

for (const viewport of [
  { name: 'mobile', width: 390, height: 844 },
  { name: 'mobile-large', width: 430, height: 932 },
]) {
  test(`${viewport.name} keeps optional entry details compact and touch safe`, async ({ page }) => {
    test.setTimeout(90_000);
    await page.setViewportSize(viewport);
    await installEntryApi(page);
    await page.goto('/entries/new');
    await expect(page.getByRole('heading', { name: 'Log your day' })).toBeVisible({
      timeout: 60_000,
    });

    const toggle = page.getByTestId('entry-more-toggle');
    await expect(toggle).toHaveAttribute('aria-expanded', 'false', { timeout: 15_000 });
    await expect(page.locator('#entry-section-tags')).not.toBeVisible();
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');

    const tag = page.getByRole('button', { name: 'Focus' });
    const symptom = page.getByRole('button', { name: 'Mild' });
    await expect(tag).toBeVisible();
    await expect(symptom).toBeVisible();

    for (const control of [toggle, tag, symptom]) {
      const box = await control.boundingBox();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }

    expect(
      await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)
    ).toBeLessThanOrEqual(0);
  });
}

test('offline autosave remains editable and recovers through retry', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const api = await installEntryApi(page);
  await page.goto('/entries/new');

  api.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event('offline')));
  await page.getByRole('button', { name: 'Increase mood' }).click();

  await expect(page.getByText('Offline — changes are not being saved.')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole('slider', { name: 'How was your day?' })).toBeEnabled();

  api.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event('online')));
  await page.getByTestId('save-status-retry').click();

  await expect(page.locator('form.entry-form')).toHaveAttribute('data-autosave-status', 'saved');
  expect(api.writes).toContain('POST /entries');
});

test('offline dexie entry saves locally and syncs after reconnect', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const api = await installEntryApi(page, { offlineSync: true });
  await page.goto('/entries/new');

  api.setOffline(true);
  await page.evaluate(() => window.dispatchEvent(new Event('offline')));
  await page.getByRole('button', { name: 'Increase mood' }).click();

  await expect(page.getByText('Offline — saved on this device. Will sync when online.')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.locator('form.entry-form')).toHaveAttribute('data-autosave-status', 'saved');

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Log your day' })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByTestId('entry-edit-hint')).toBeVisible({ timeout: 15_000 });

  api.setOffline(false);
  await page.evaluate(() => window.dispatchEvent(new Event('online')));
  await page.getByTestId('save-status').click().catch(() => undefined);

  await expect
    .poll(() => api.syncWrites.includes('POST /sync/push'), { timeout: 15_000 })
    .toBe(true);
});

test('desktop keeps optional entry details expanded', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await installEntryApi(page);
  await page.goto('/entries/new');

  await expect(page.getByTestId('entry-more-toggle')).toHaveCount(0);
  await expect(page.locator('#entry-section-tags')).toBeVisible();
});

test('historical day outside the edit window is read-only', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installEntryApi(page, { historical: true });
  await page.goto('/entries/day/2026-01-01');

  await expect(page.getByTestId('day-entry-read-only')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Edit', exact: true })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Add or edit', exact: true })).toHaveCount(0);
});
