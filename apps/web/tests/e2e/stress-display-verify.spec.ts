import { expect, test } from '@playwright/test';

test('home work-context heatmap inverts stress (lower stress = stronger cell)', async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem('dev_mode_enabled', 'true');
    localStorage.setItem('dev_force_viz', 'true');
  });

  await page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'user-1',
        email: 'stress@example.com',
        display_name: 'Stress',
        is_verified: true,
      }),
    });
  });

  await page.route('**/api/v1/auth/refresh', async (route) => {
    await route.fulfill({ status: 204, body: '' });
  });

  await page.route('**/api/v1/insights**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        insight_maturity: {
          phase: 'provisional',
          phase_index: 3,
          current_entries: 21,
          next_phase_at: 30,
          next_phase_label: 'Robust Insights',
          entries_until_next: 9,
          user_message_key: 'maturity.provisional.description',
        },
        insights: [],
      }),
    });
  });

  await page.route('**/api/v1/entries**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/v1/dashboard**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        entry_count: 21,
        insight_tier: 'preliminary',
        confidence_score: 0.48,
        work_context_summary: [
          {
            work_context: 'office',
            entry_count: 9,
            mood_avg: 3.4,
            energy_avg: 3.2,
            stress_avg: 3.6,
          },
          {
            work_context: 'homeoffice',
            entry_count: 8,
            mood_avg: 3.9,
            energy_avg: 3.7,
            stress_avg: 2.8,
          },
          {
            work_context: 'vacation',
            entry_count: 4,
            mood_avg: 4.2,
            energy_avg: 3.8,
            stress_avg: 2.2,
          },
        ],
      }),
    });
  });

  await page.route('**/api/v1/user/preferences**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user_id: 'user-1',
        analytics_enabled: true,
        onboarding_retro_completed: true,
        onboarding_profile_completed: true,
        onboarding_maturity_intro_seen: true,
        dismissed_insight_keys: [],
        reached_milestone_keys: [],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }),
    });
  });

  await page.goto('/');

  const heatmap = page.getByTestId('home-work-context-heatmap');
  await expect(heatmap).toBeVisible();

  const rows = heatmap.locator('.work-context-summary__row');
  await expect(rows).toHaveCount(3);

  // Read the stress cell (raw value + intensity level) per work context.
  const stressByContext = await rows.evaluateAll((nodes) =>
    Object.fromEntries(
      nodes.map((row) => {
        const context = row.getAttribute('data-context') ?? '';
        const cell = row.querySelector('[data-metric="stress"]') as HTMLElement | null;
        return [
          context,
          {
            level: Number(cell?.getAttribute('data-level')),
            value: cell?.textContent?.trim() ?? '',
          },
        ];
      })
    )
  );

  // Raw stress averages are shown unchanged in the cell.
  expect(stressByContext.vacation.value).toBe('2.2');
  expect(stressByContext.office.value).toBe('3.6');
  expect(stressByContext.homeoffice.value).toBe('2.8');

  // Stress is inverted for shading: lower raw stress -> higher goodness -> stronger level.
  // vacation 2.2 (goodness 3.8) > homeoffice 2.8 (3.2) > office 3.6 (2.4)
  expect(stressByContext.vacation.level).toBeGreaterThan(stressByContext.homeoffice.level);
  expect(stressByContext.homeoffice.level).toBeGreaterThan(stressByContext.office.level);

  // Best overall situation (vacation) is ordered first.
  const firstContext = await rows.first().getAttribute('data-context');
  expect(firstContext).toBe('vacation');

  // Token-based single-hue ramp — no red/green semantic colours on the cells.
  const cellBackgrounds = await heatmap
    .locator('.work-context-summary__cell')
    .evaluateAll((cells) => cells.map((cell) => getComputedStyle(cell).backgroundColor));
  for (const background of cellBackgrounds) {
    expect(background).not.toMatch(/239,\s*68,\s*68|ef4444/i); // metric-stress red
    expect(background).not.toMatch(/22,\s*163,\s*74|16a34a/i); // success green
  }
});
